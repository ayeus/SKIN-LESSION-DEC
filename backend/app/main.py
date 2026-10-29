import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from typing import Annotated, Literal
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from .db import Base, engine, Session, Dataset, Run, Audit, ROOT
from .services import images, tabular, analytics, text
from . import training

logging.basicConfig(level=logging.INFO,format='%(message)s'); logger=logging.getLogger('dermainsight')
security=HTTPBearer(auto_error=False)
executor=ThreadPoolExecutor(max_workers=2,thread_name_prefix='research-job')
queue_slots=BoundedSemaphore(4)

@asynccontextmanager
async def lifespan(app):
    # Migrations own schema creation. Local opt-in only, production uses alembic upgrade head.
    if os.getenv('DERMA_DEV_CREATE_SCHEMA')=='1': Base.metadata.create_all(engine)
    with Session() as s:
        for run in s.scalars(select(Run).where(Run.status.in_(['pending','running']))):
            run.status='failed'; run.error='Process interrupted; rerun explicitly'
        s.commit()
    yield

app=FastAPI(title='DermaInsight AI Research API',version='0.1.0',lifespan=lifespan)

def auth(credentials: Annotated[HTTPAuthorizationCredentials|None,Depends(security)]):
    token=os.getenv('DERMA_API_TOKEN','')
    if len(token)<24: raise HTTPException(503,'Configure DERMA_API_TOKEN with at least 24 characters')
    if not credentials or not hmac.compare_digest(credentials.credentials,token): raise HTTPException(401,'Valid research access token required')

Protected=Annotated[None,Depends(auth)]

def audit(action,resource):
    with Session() as s: s.add(Audit(id=str(uuid4()),action=action,resource_id=resource)); s.commit()

def serialize(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns if c.name!='path'}

def get_dataset(id):
    with Session() as s: item=s.get(Dataset,id)
    if item is None: raise HTTPException(404,'Dataset not found')
    audit('dataset_read',id); return item

async def upload_bytes(file):
    data=await file.read(20*1024*1024+1)
    if len(data)>20*1024*1024: raise HTTPException(413,'Upload limit is 20 MiB')
    if not data: raise HTTPException(422,'Empty upload')
    return data

def execute(kind,parameters,fn,dataset_id=None,run_id=None):
    id=run_id or str(uuid4())
    with Session() as s:
        if run_id:
            run=s.get(Run,id); run.status='running'
        else: s.add(Run(id=id,kind=kind,dataset_id=dataset_id,parameters=parameters,status='running',result={}))
        s.commit()
    try:
        result=tabular.clean_json(fn(id))
        directory=ROOT/'processed'/id; directory.mkdir(parents=True,exist_ok=True)
        (directory/'report.json').write_text(json.dumps(result,allow_nan=False,indent=2))
        with Session() as s: run=s.get(Run,id); run.status='completed'; run.result={'artifact':'report.json'}; s.commit()
        audit(kind,id); return {'id':id,'status':'completed','result':result}
    except Exception as e:
        with Session() as s: run=s.get(Run,id); run.status='failed'; run.error=str(e); s.commit()
        logger.info(json.dumps({'event':'run_failed','run_id':id,'kind':kind,'exception':type(e).__name__}))
        if isinstance(e,(ValueError,KeyError,TypeError)): raise HTTPException(422,str(e)) from e
        raise HTTPException(500,f'Execution failed; inspect local logs and run {id}') from e

@app.get('/health')
def health(): return {'status':'alive','research_only':True}

def model_ready():
    directory=training.selected_directory()
    if not directory: return False
    try:
        from .services.ml import load_artifact
        load_artifact(Path(directory)); return True
    except (OSError,ValueError,KeyError,RuntimeError): return False

@app.get('/status')
def status(_:Protected):
    with Session() as s:
        datasets=list(s.scalars(select(Dataset))); runs=list(s.scalars(select(Run)))
    return {'datasets':len(datasets),'processed_images':sum(r.kind=='image' and r.status=='completed' for r in runs),
        'runs':len(runs),'completed_runs':sum(r.status=='completed' for r in runs),'failed_runs':sum(r.status=='failed' for r in runs),
        'modalities':dict(__import__('collections').Counter(d.modality for d in datasets)),
        'model_available':model_ready(),
        'clinical_validation':'Not established','ner':'Configured; research-only, validation must be reviewed' if os.getenv('DERMA_NER_MODEL') else 'BLOCKED: licensed clinical model not configured'}

@app.get('/datasets')
def datasets(_:Protected):
    audit('dataset_list','registry')
    with Session() as s: return [serialize(d) for d in s.scalars(select(Dataset).order_by(Dataset.created_at.desc()))]

@app.post('/datasets')
async def import_dataset(_:Protected,file:UploadFile=File(...),modality:Literal['ehr','clinical_text','demand','weight','tabular']=Form(...),source:str=Form(...),license:str=Form(...),authorized:bool=Form(...)):
    if not authorized: raise HTTPException(422,'Confirm authorized de-identified research use')
    if not source.strip() or not license.strip(): raise HTTPException(422,'Source and license required')
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ('.csv','.xlsx','.json'): raise HTTPException(422,'Use CSV, XLSX or the documented FHIR JSON subset')
    data=await upload_bytes(file)
    if suffix=='.json':
        if modality!='ehr':raise HTTPException(422,'FHIR imports require EHR modality')
        try:
            from .services.fhir import parse
            parse(data)  # Reject identifying/unsupported fields before persisting raw bytes.
        except ValueError as error:raise HTTPException(422,str(error)) from error
    if suffix=='.xlsx':
        from zipfile import ZipFile, BadZipFile
        import io
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(info.file_size for info in archive.infolist())>100*1024*1024:
                    raise HTTPException(422,'XLSX decompressed size exceeds 100 MiB')
        except BadZipFile as e: raise HTTPException(422,'Invalid XLSX archive') from e
    id=str(uuid4()); path=ROOT/'raw'/id/('source'+suffix); path.parent.mkdir(parents=True); path.write_bytes(data)
    try: frame=tabular.read_table(path); profile=tabular.profile(frame)
    except (ValueError,UnicodeError,KeyError,OSError) as e: path.unlink(); raise HTTPException(422,str(e)) from e
    with Session() as s:
        row=Dataset(id=id,name=Path(file.filename or 'dataset').name[:200],modality=modality,source=source,license=license,sha256=hashlib.sha256(data).hexdigest(),path=str(path),profile=profile); s.add(row); s.commit()
    audit('dataset_import',id); return serialize(row)

@app.get('/datasets/{id}')
def dataset(id:str,_:Protected): return serialize(get_dataset(id))

class Operation(BaseModel):
    dataset_id:str
    parameters:dict=Field(default_factory=dict)

@app.post('/analyze/{kind}')
def analyze(kind:Literal['preprocess','forecast','research','reduce','text','overview'],body:Operation,_:Protected,background:bool=False):
    dataset=get_dataset(body.dataset_id); df=tabular.read_table(Path(dataset.path)); p=body.parameters
    allowed={'preprocess':{'ehr','tabular','weight'},'forecast':{'demand'},'research':{'weight','tabular'},'reduce':{'ehr','weight','tabular'},'text':{'clinical_text'},'overview':{'ehr','demand','weight','tabular','clinical_text'}}
    if dataset.modality not in allowed[kind]: raise HTTPException(422,f'{kind} is incompatible with {dataset.modality}')
    def work(id):
        if kind=='preprocess':
            output,result=tabular.transform(df,p); directory=ROOT/'processed'/id; directory.mkdir(parents=True,exist_ok=True); output.to_csv(directory/'transformed.csv',index=False); return result
        if kind=='forecast': return analytics.forecast(df,p)
        if kind=='research': return analytics.research(df,p)
        if kind=='reduce': return analytics.reduce(df,p)
        if kind=='text': return text.analyze(df,p)
        return analytics.strategic(df,p)
    if not background: return execute(kind,p,work,dataset.id)
    if not queue_slots.acquire(blocking=False): raise HTTPException(429,'Research queue is full; wait for an existing job')
    id=str(uuid4())
    try:
        with Session() as session:
            session.add(Run(id=id,kind=kind,dataset_id=dataset.id,parameters=p,status='pending',result={})); session.commit()
        def worker():
            try: execute(kind,p,work,dataset.id,run_id=id)
            except HTTPException: pass  # Failure is persisted by execute; polling returns the actual error.
            finally: queue_slots.release()
        executor.submit(worker)
    except Exception:
        queue_slots.release(); raise
    return {'id':id,'status':'pending'}

@app.post('/images/process')
async def process_image(_:Protected,file:UploadFile=File(...),method:str=Form(...),parameters:str=Form('{}'),mask:UploadFile|None=File(None)):
    data=await upload_bytes(file)
    try:
        rgb=images.decode(data); p=json.loads(parameters)
        if not isinstance(p,dict): raise ValueError('Parameters must be a JSON object')
        truth=images.decode(await upload_bytes(mask))[:,:,0] if mask else None
    except (ValueError,json.JSONDecodeError) as e: raise HTTPException(422,str(e)) from e
    def work(id):
        result=images.process(rgb,method,p)
        if result['mask'] and truth is not None:
            import base64
            predicted=images.decode(base64.b64decode(result['mask'].split(',')[1]))[:,:,0]
            result['metrics'].update(images.mask_metrics(predicted,truth))
        # Only generated artifact is retained; no raw upload or EXIF persisted.
        return result
    return execute('image',{'method':method,**p},work)

@app.post('/images/register')
async def registration(_:Protected,first:UploadFile=File(...),second:UploadFile=File(...)):
    try: a=images.decode(await upload_bytes(first)); b=images.decode(await upload_bytes(second))
    except ValueError as e: raise HTTPException(422,str(e)) from e
    return execute('registration',{},lambda id:images.register(a,b))

@app.post('/inference')
async def inference(_:Protected,file:UploadFile=File(...),explain:bool=Form(False),retain:bool=Form(False)):
    model=training.selected_directory()
    if not model: raise HTTPException(409,'No trained lesion model configured. Supply validated dataset, train and set DERMA_MODEL_DIR.')
    try: rgb=images.decode(await upload_bytes(file))
    except ValueError as e: raise HTTPException(422,str(e)) from e
    from .services.ml import predict,gradcam
    # Image bytes are never retained here. Scores are stored only with explicit opt-in.
    audit('inference_requested','ephemeral')
    try:
        result=predict(rgb,Path(model))
        result['input_rgb_sha256']=hashlib.sha256(rgb.tobytes()).hexdigest()
        result['input_shape']=list(rgb.shape)
        if explain: result['explanation']=gradcam(rgb,Path(model))
        result['retention']='Scores and model/input hashes saved; image bytes and Grad-CAM image not retained' if retain else 'Ephemeral; no scores or image bytes retained'
        if retain:
            persisted={key:value for key,value in result.items() if key!='explanation'}
            saved=execute('inference',{'retain_scores':True,'retain_image':False},lambda id:persisted)
            result['saved_run_id']=saved['id']
        return result
    except (OSError,ValueError,KeyError,RuntimeError) as e: raise HTTPException(409,'Model artifact cannot be used: '+str(e)) from e

@app.get('/runs')
def runs(_:Protected):
    with Session() as s: return [dict(id=r.id,kind=r.kind,dataset_id=r.dataset_id,status=r.status,error=r.error,created_at=r.created_at) for r in s.scalars(select(Run).order_by(Run.created_at.desc()).limit(100))]

@app.get('/runs/{id}')
def run(id:str,_:Protected):
    with Session() as s: item=s.get(Run,id)
    if item is None: raise HTTPException(404,'Run not found')
    audit('run_read',id)
    payload=serialize(item)
    if item.status=='completed' and item.result.get('artifact')=='report.json':
        path=ROOT/'processed'/item.id/'report.json'
        if not path.is_file(): raise HTTPException(409,'Execution artifact is missing from storage')
        payload['result']=json.loads(path.read_text())
    return payload

@app.get('/runs/{id}/export/{format}')
def export(id:str,format:Literal['json','csv'],_:Protected):
    with Session() as s: item=s.get(Run,id)
    if item is None: raise HTTPException(404,'Run not found')
    path=ROOT/'processed'/item.id/('report.json' if format=='json' else 'transformed.csv')
    if not path.is_file(): raise HTTPException(404,'Requested artifact is unavailable for this run')
    audit('artifact_export',id); return FileResponse(path,filename=f'{item.kind}-{id}.{format}')

@app.get('/models/current')
def current_model(_:Protected):
    if not model_ready(): raise HTTPException(409,'No usable trained model artifact configured')
    root=training.selected_directory()
    audit('model_review','current')
    return {'manifest':json.loads((root/'manifest.json').read_text()),'history':json.loads((root/'history.json').read_text())}


training_slot=BoundedSemaphore(1)

class TrainingRequest(BaseModel):
    architecture:Literal['small_cnn','resnet18','efficientnet_b0']='small_cnn'
    epochs:int=Field(default=5,ge=1,le=1000)
    batch_size:int=Field(default=16,ge=1,le=128)
    pretrained:bool=False

@app.get('/training/readiness')
def training_readiness(_:Protected):return training.readiness()

@app.post('/training')
def start_training(body:TrainingRequest,_:Protected):
    ready=training.readiness()
    if not ready['ready']:raise HTTPException(409,ready['reason'])
    if not training_slot.acquire(blocking=False):raise HTTPException(409,'Another CNN training run is active')
    if not queue_slots.acquire(blocking=False):
        training_slot.release();raise HTTPException(429,'Research queue is full')
    id=str(uuid4());params=body.model_dump()
    try:
        with Session() as s:s.add(Run(id=id,kind='training',parameters=params,status='pending',result={}));s.commit()
        def worker():
            try:
                def work(run_id):
                    from .services.ml import train
                    metadata,images=training.source_paths()
                    def progress(epoch):
                        with Session() as s:
                            item=s.get(Run,run_id);item.result={'epoch':epoch['epoch'],'total_epochs':body.epochs,'latest':epoch};s.commit()
                    manifest=train(metadata,images,training.artifact_dir(run_id),name=body.architecture,epochs=body.epochs,batch_size=body.batch_size,pretrained=body.pretrained,progress_callback=progress)
                    return {'manifest':manifest,'history':json.loads((training.artifact_dir(run_id)/'history.json').read_text()),'training_run_id':run_id}
                execute('training',params,work,run_id=id)
            except HTTPException:pass  # execute persists and exposes failure; never convert to success.
            finally:training_slot.release();queue_slots.release()
        executor.submit(worker)
    except Exception:
        training_slot.release();queue_slots.release();raise
    audit('training_submitted',id)
    return {'id':id,'status':'pending'}

@app.post('/models/select/{id}')
def select_model(id:str,_:Protected):
    with Session() as s:item=s.get(Run,id)
    if item is None:raise HTTPException(404,'Training run not found')
    if item.kind!='training' or item.status!='completed':raise HTTPException(409,'Select only a completed training run after reviewing its evaluation')
    if os.getenv('DERMA_MODEL_DIR'):raise HTTPException(409,'DERMA_MODEL_DIR overrides selection; remove that setting before selecting through the UI')
    try:result=training.select_artifact(item.id)
    except (ValueError,OSError,KeyError,RuntimeError) as e:raise HTTPException(409,'Artifact validation failed: '+str(e)) from e
    audit('research_model_selected',id);return result

@app.get('/datasets/{id}/rows')
def dataset_rows(id:str,_:Protected,offset:int=0,limit:int=25,column:str|None=None,value:str|None=None,match:Literal['equals','contains']='equals'):
    if offset<0 or not 1<=limit<=100:raise HTTPException(422,'Use nonnegative offset and limit between 1 and 100')
    dataset=get_dataset(id);frame=tabular.read_table(Path(dataset.path))
    if column:
        if column not in frame or value is None:raise HTTPException(422,'Filter requires an existing column and a value')
        series=frame[column]
        if match=='contains':
            mask=series.astype('string').str.contains(value,case=False,regex=False,na=False)
        elif __import__('pandas').api.types.is_numeric_dtype(series):
            try: number=float(value)
            except ValueError as error:raise HTTPException(422,'Numeric column requires a numeric filter value') from error
            if not __import__('math').isfinite(number):raise HTTPException(422,'Filter must be finite')
            mask=series.eq(number)
        else:mask=series.astype('string').eq(value).fillna(False)
        frame=frame.loc[mask]
    audit('dataset_filtered_read',id)
    return {'offset':offset,'limit':limit,'matched_rows':len(frame),'columns':list(frame.columns),'rows':tabular.clean_json(frame.iloc[offset:offset+limit].to_dict('records'))}

class RelationshipRequest(BaseModel):
    child_dataset_id:str
    parent_dataset_id:str
    child_key:str
    parent_key:str

@app.post('/relationships')
def relationship(body:RelationshipRequest,_:Protected):
    from .services.relationships import inspect
    child=get_dataset(body.child_dataset_id);parent=get_dataset(body.parent_dataset_id)
    if child.modality!='ehr' or parent.modality!='ehr':raise HTTPException(422,'Relationship inspection requires authorized EHR tables')
    return execute('relationship',body.model_dump(),lambda id:inspect(tabular.read_table(Path(child.path)),tabular.read_table(Path(parent.path)),body.child_key,body.parent_key),child.id)
