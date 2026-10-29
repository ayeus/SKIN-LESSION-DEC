"""Actual tiny training on isolated synthetic pixels; never a real lesion artifact."""
import os
import time
import numpy as np
import pandas as pd
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app
H={'Authorization':'Bearer synthetic-test-token-not-a-secret'}

def test_missing_dataset_blocks_and_does_not_promote(monkeypatch,tmp_path):
    monkeypatch.setenv('DERMA_LESION_METADATA',str(tmp_path/'absent.csv'))
    with TestClient(app) as client:
        assert client.get('/training/readiness').status_code==401
        assert client.get('/training/readiness',headers=H).json()['ready'] is False
        assert client.post('/training',headers=H,json={}).status_code==409
        assert client.post('/training',headers=H,json={'epochs':0}).status_code==422
        assert client.post('/models/select/not-present',headers=H).status_code==404

def test_training_progress_artifact_selection_and_real_inference(monkeypatch,tmp_path):
    from backend.app.db import ROOT
    monkeypatch.delenv('DERMA_MODEL_DIR',raising=False)
    images=tmp_path/'images';images.mkdir();rows=[]
    for label in ['a','b']:
        for group in range(10):
            name=f'{label}-{group}.png'
            pixels=np.random.default_rng(group+(100 if label=='b' else 0)).integers(0,256,(32,32,3),dtype=np.uint8)
            Image.fromarray(pixels).save(images/name);rows.append({'image_path':name,'label':label,'group_id':name})
    path=tmp_path/'metadata.csv';pd.DataFrame(rows).to_csv(path,index=False)
    monkeypatch.setenv('DERMA_LESION_METADATA',str(path));monkeypatch.setenv('DERMA_LESION_IMAGES',str(images))
    pointer=ROOT/'model-selection.json'
    try:
        with TestClient(app) as client:
            assert client.get('/training/readiness',headers=H).json()['ready'] is True
            job=client.post('/training',headers=H,json={'epochs':1,'batch_size':4})
            assert job.status_code==200,job.text
            id=job.json()['id']
            for _ in range(500):
                run=client.get('/runs/'+id,headers=H).json()
                if run['status'] in ['completed','failed']:break
                time.sleep(.02)
            assert run['status']=='completed',run
            assert run['result']['manifest']['epochs']==1
            assert len(run['result']['history'])==1
            assert not pointer.exists()  # No implicit promotion.
            selected=client.post('/models/select/'+id,headers=H)
            assert selected.status_code==200,selected.text
            assert client.get('/models/current',headers=H).json()['manifest']['research_only']
            output=client.post('/inference',headers=H,files={'file':('synthetic.png',(images/'a-0.png').read_bytes(),'image/png')})
            assert output.status_code==200,output.text
            assert set(output.json()['scores'])=={'a','b'}
    finally:
        pointer.unlink(missing_ok=True)  # Isolated test storage only.
