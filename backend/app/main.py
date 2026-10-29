import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from typing import Annotated, Literal
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from .db import Base, engine, Session, Dataset, Run, Audit, ROOT
from .services import images, tabular, analytics, text

logging.basicConfig(level=logging.INFO,format='%(message)s'); logger=logging.getLogger('dermainsight')
security=HTTPBearer(auto_error=False)

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

def execute(kind,parameters,fn,dataset_id=None):
    id=str(uuid4())
    with Session() as s: s.add(Run(id=id,kind=kind,dataset_id=dataset_id,parameters=parameters,status='running',result={})); s.commit()
    try:
        result=tabular.clean_json(fn(id))
        directory=ROOT/'processed'/id; directory.mkdir(parents=True,exist_ok=True)
        (directory/'report.json').write_text(json.dumps(result,allow_nan=False,indent=2))
        with Session() as s: run=s.get(Run,id); run.status='completed'; run.result=result; s.commit()
        audit(kind,id); return {'id':id,'status':'completed','result':result}
    except Exception as e:
        with Session() as s: run=s.get(Run,id); run.status='failed'; run.error=str(e); s.commit()
        logger.info(json.dumps({'event':'run_failed','run_id':id,'kind':kind,'exception':type(e).__name__}))
        if isinstance(e,(ValueError,KeyError,TypeError)): raise HTTPException(422,str(e)) from e
        raise HTTPException(500,f'Execution failed; inspect local logs and run {id}') from e

@app.get('/health')
def health(): return {'status':'alive','research_only':True}

@app.get('/status')
def status(_:Protected):
    with Session() as s:
        datasets=list(s.scalars(select(Dataset))); runs=list(s.scalars(select(Run)))
    return {'datasets':len(datasets),'processed_images':sum(r.kind=='image' and r.status=='completed' for r in runs),
        'runs':len(runs),'completed_runs':sum(r.status=='completed' for r in runs),'failed_runs':sum(r.status=='failed' for r in runs),
        'modalities':dict(__import__('collections').Counter(d.modality for d in datasets)),
        'model_available':bool(os.getenv('DERMA_MODEL_DIR') and (Path(os.environ['DERMA_MODEL_DIR'])/'manifest.json').is_file()),
        'clinical_validation':'Not established','ner':'BLOCKED: licensed clinical model not configured'}

@app.get('/datasets')
def datasets(_:Protected):
    with Session() as s: return [serialize(d) for d in s.scalars(select(Dataset).order_by(Dataset.created_at.desc()))]

@app.post('/datasets')
async def import_dataset(_:Protected,file:UploadFile=File(...),modality:Literal['ehr','clinical_text','demand','weight','tabular']=Form(...),source:str=Form(...),license:str=Form(...),authorized:bool=Form(...)):
    if not authorized: raise HTTPException(422,'Confirm authorized de-identified research use')
    if not source.strip() or not license.strip(): raise HTTPException(422,'Source and license required')
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ('.csv','.xlsx'): raise HTTPException(422,'Use CSV or XLSX')
    data=await upload_bytes(file); id=str(uuid4()); path=ROOT/'raw'/id/('source'+suffix); path.parent.mkdir(parents=True); path.write_bytes(data)
    try: frame=tabular.read_table(path); profile=tabular.profile(frame)
    except (ValueError,UnicodeError,KeyError) as e: path.unlink(); raise HTTPException(422,str(e)) from e
    with Session() as s:
        row=Dataset(id=id,name=Path(file.filename or 'dataset').name[:200],modality=modality,source=source,license=license,sha256=hashlib.sha256(data).hexdigest(),path=str(path),profile=profile); s.add(row); s.commit()
    audit('dataset_import',id); return serialize(row)

@app.get('/datasets/{id}')
def dataset(id:str,_:Protected): return serialize(get_dataset(id))

class Operation(BaseModel):
    dataset_id:str
    parameters:dict=Field(default_factory=dict)

@app.post('/analyze/{kind}')
def analyze(kind:Literal['preprocess','forecast','research','reduce','text','overview'],body:Operation,_:Protected):
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
        return tabular.profile(df)
    return execute(kind,p,work,dataset.id)

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
async def inference(_:Protected,file:UploadFile=File(...)):
    model=os.getenv('DERMA_MODEL_DIR')
    if not model: raise HTTPException(409,'No trained lesion model configured. Supply validated dataset, train and set DERMA_MODEL_DIR.')
    try: rgb=images.decode(await upload_bytes(file))
    except ValueError as e: raise HTTPException(422,str(e)) from e
    from .services.ml import predict
    # Inference image and scores are not persisted; explicit retention workflow is not yet supported.
    audit('inference_requested','ephemeral'); return predict(rgb,Path(model))

@app.get('/runs')
def runs(_:Protected):
    with Session() as s: return [dict(id=r.id,kind=r.kind,dataset_id=r.dataset_id,status=r.status,error=r.error,created_at=r.created_at) for r in s.scalars(select(Run).order_by(Run.created_at.desc()).limit(100))]

@app.get('/runs/{id}')
def run(id:str,_:Protected):
    with Session() as s: item=s.get(Run,id)
    if item is None: raise HTTPException(404,'Run not found')
    audit('run_read',id); return serialize(item)

@app.get('/runs/{id}/export/{format}')
def export(id:str,format:Literal['json','csv'],_:Protected):
    with Session() as s: item=s.get(Run,id)
    if item is None: raise HTTPException(404,'Run not found')
    path=ROOT/'processed'/item.id/('report.json' if format=='json' else 'transformed.csv')
    if not path.is_file(): raise HTTPException(404,'Requested artifact is unavailable for this run')
    audit('artifact_export',id); return FileResponse(path,filename=f'{item.kind}-{id}.{format}')
