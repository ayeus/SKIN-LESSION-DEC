import io
import json
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app
H={'Authorization':'Bearer synthetic-test-token-not-a-secret'}

def test_auth_import_transform_export_persistence():
    with TestClient(app) as client:
        assert client.get('/status').status_code==401
        raw=b'Patient,Encounter,Value\n1,10,2\n1,11,4\n1,11,4\n'
        data={'modality':'ehr','source':'explicit synthetic unit test','license':'test-only','authorized':'true'}
        imported=client.post('/datasets',headers=H,data=data,files={'file':('fixture.csv',raw,'text/csv')})
        assert imported.status_code==200,imported.text
        id=imported.json()['id']; assert imported.json()['profile']['rows']==3
        run=client.post('/analyze/preprocess',headers=H,json={'dataset_id':id,'parameters':{'drop_exact_duplicates':True}})
        assert run.status_code==200,run.text
        rid=run.json()['id']; assert run.json()['result']['after']['rows']==2
        assert client.get('/runs/'+rid,headers=H).json()['status']=='completed'
        exported=client.get(f'/runs/{rid}/export/csv',headers=H); assert exported.status_code==200; assert 'patient,encounter,value' in exported.text
        assert client.get('/datasets/'+id,headers=H).json()['profile']['rows']==3
        assert client.post('/analyze/forecast',headers=H,json={'dataset_id':id}).status_code==422
        assert client.post('/inference',headers=H,files={'file':('x.png',b'bad')}).status_code==409
        assert client.get('/runs/not-an-id/export/json',headers=H).status_code==404

def test_image_api_and_failure_is_persisted():
    image=Image.fromarray(np.full((32,32,3),120,np.uint8)); stream=io.BytesIO(); image.save(stream,format='PNG')
    with TestClient(app) as client:
        result=client.post('/images/process',headers=H,data={'method':'png','parameters':'{}'},files={'file':('synthetic.png',stream.getvalue(),'image/png')})
        assert result.status_code==200,result.text
        assert result.json()['result']['metrics']['lossless']
        bad=client.post('/images/process',headers=H,data={'method':'nonexistent'},files={'file':('synthetic.png',stream.getvalue(),'image/png')})
        assert bad.status_code==422
        assert any(r['status']=='failed' for r in client.get('/runs',headers=H).json())
        assert client.post('/images/process',headers=H,data={'method':'png'},files={'file':('bad.png',b'bad')}).status_code==422

def test_import_requires_authorization_and_provenance():
    with TestClient(app) as client:
        r=client.post('/datasets',headers=H,data={'modality':'ehr','source':'fixture','license':'test','authorized':'false'},files={'file':('x.csv',b'a\n1')})
        assert r.status_code==422

def test_background_run_reaches_persisted_terminal_state():
    import time
    with TestClient(app) as client:
        data={'modality':'tabular','source':'synthetic job test','license':'test','authorized':'true'}
        id=client.post('/datasets',headers=H,data=data,files={'file':('synthetic.csv',b'x,z\n1,2\n2,4\n3,6\n4,8')}).json()['id']
        job=client.post('/analyze/reduce?background=true',headers=H,json={'dataset_id':id,'parameters':{'features':['x','z']}})
        assert job.status_code==200,job.text
        for _ in range(100):
            run=client.get('/runs/'+job.json()['id'],headers=H).json()
            if run['status'] in ('completed','failed'): break
            time.sleep(.02)
        assert run['status']=='completed',run
        assert len(run['result']['coordinates'])==4
