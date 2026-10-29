import pandas as pd
import pytest
from backend.app.services.relationships import inspect
from fastapi.testclient import TestClient
from backend.app.main import app
H={'Authorization':'Bearer synthetic-test-token-not-a-secret'}

def test_relationships_preserve_multiple_encounters_and_flag_orphans():
    result=inspect(pd.DataFrame({'patient':[1,1,2,9,None]}),pd.DataFrame({'id':[1,2,3]}),'patient','id')
    assert result['matched_child_rows']==3 and result['unmatched_nonmissing_child_rows']==1
    assert result['missing_child_keys']==1 and result['parents_without_children']==1
    with pytest.raises(ValueError,match='unique'):inspect(pd.DataFrame({'patient':[1]}),pd.DataFrame({'id':[1,1]}),'patient','id')

def test_authenticated_browsing_pagination_literal_filters_and_relationship_api():
    with TestClient(app) as client:
        def upload(name,data):return client.post('/datasets',headers=H,data={'modality':'ehr','source':'synthetic tests','license':'test only','authorized':'true'},files={'file':(name,data)}).json()['id']
        parent=upload('parent.csv',b'id\n1\n2\n3\n');child=upload('child.csv',b'patient,note\n1,alpha.*\n1,beta\n2,alpha\n')
        assert client.get('/datasets/'+child+'/rows').status_code==401
        response=client.get('/datasets/'+child+'/rows',headers=H,params={'column':'patient','value':'1','offset':1,'limit':1})
        assert response.status_code==200 and response.json()['matched_rows']==2 and response.json()['rows'][0]['note']=='beta'
        literal=client.get('/datasets/'+child+'/rows',headers=H,params={'column':'note','value':'.*','match':'contains'}).json()
        assert literal['matched_rows']==1
        assert client.get('/datasets/'+child+'/rows',headers=H,params={'limit':10000}).status_code==422
        assert client.get('/datasets/'+child+'/rows',headers=H,params={'column':'patient','value':'not-a-number'}).status_code==422
        relationship=client.post('/relationships',headers=H,json={'child_dataset_id':child,'parent_dataset_id':parent,'child_key':'patient','parent_key':'id'})
        assert relationship.status_code==200 and relationship.json()['result']['matched_child_rows']==3
