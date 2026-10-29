import numpy as np
import pandas as pd
import pytest
from backend.app.services.tabular import transform,profile
from backend.app.services.analytics import forecast,reduce,research
from backend.app.services.text import analyze

def test_transform_preserves_source_and_repeated_encounters():
    df=pd.DataFrame({'Patient ID':[1,1,1],'Encounter':[2,3,3],'Value':[' 10 ','20','20']}); original=df.copy(deep=True)
    out,r=transform(df,{'types':{'value':'numeric'},'drop_exact_duplicates':True,'duplicate_keys':['patient_id']})
    pd.testing.assert_frame_equal(df,original); assert len(out)==2; assert out.encounter.tolist()==[2,3]
    assert r['history'][-1]['removed']==1; assert len(r['manual_review'][-1]['rows'])==2

def test_missing_invalid_units_and_collision():
    df=pd.DataFrame({'x':['1',None,'bad'],'temp':[32,212,50]})
    out,r=transform(df,{'types':{'x':'numeric'},'impute':{'x':'median'},'units':{'temp':{'factor':5/9,'offset':-32*5/9,'from':'F','to':'C'}},'ranges':{'temp':[0,50]}})
    assert out.x.tolist()==[1,1,1]; assert out.temp.iloc[1]==pytest.approx(100)
    assert r['manual_review'][0]['rows']==[2]; assert r['manual_review'][1]['rows']==[1]
    with pytest.raises(ValueError): transform(pd.DataFrame({'A A':[1],'a_a':[2]}),{})

def demand(): return pd.DataFrame({'date':pd.date_range('2020-01-01',periods=70).strftime('%Y-%m-%d'),'count':np.tile([4,8,12,16,20,24,28],10)})

def test_forecast_seasonality_and_explicit_scenario():
    result=forecast(demand(),{'patients_per_staff_per_shift':4})
    assert result['selected']=='weekly_seasonal'; assert result['validation_metrics']['weekly_seasonal']['mae']==0
    assert [v['count'] for v in result['forecast']]==[4,8,12,16,20,24,28]
    assert result['scenario']['staff_per_shift']==[1,2,3,4,5,6,7]
    assert 'scenario' not in forecast(demand(),{})

def test_missing_dates_and_negative_counts_rejected():
    with pytest.raises(ValueError,match='Missing days'): forecast(demand().drop(index=10),{})
    bad=demand(); bad.loc[0,'count']=-1
    with pytest.raises(ValueError): forecast(bad,{})

def test_temporal_validation_does_not_see_future():
    a=demand(); b=a.copy(); b.loc[69,'count']=1000
    ra=forecast(a,{}); rb=forecast(b,{})
    # Validation predictions at the final origin remain seasonal baseline from t-7;
    # final shock changes only residual, never the prediction at that origin.
    assert rb['validation_metrics']['weekly_seasonal']['mae']==pytest.approx((1000-28)/14)
    assert ra['validation_metrics']['weekly_seasonal']['mae']==0

def test_pca_and_held_out_regression():
    x=np.arange(80,dtype=float); df=pd.DataFrame({'x':x,'z':x*2,'y':x*3+5})
    r=reduce(df,{'features':['x','z']}); assert r['explained_variance_ratio'][0]==pytest.approx(1)
    m=research(df,{'features':['x','z'],'target':'y'}); assert m['test_rows']==20; assert m['r2']>.99
    with pytest.raises(ValueError): research(df,{'features':['x','y'],'target':'y'})

def test_bm25_ranking_and_ner_block():
    df=pd.DataFrame({'text':['lesion lesion dermoscopy','cardiac rhythm review','skin lesion inspection','cardiac valve imaging']})
    r=analyze(df,{'task':'search','query':'dermoscopy'}); assert r['results'][0]['document_index']==0
    assert r['disambiguation']['status']=='unresolved'
    with pytest.raises(ValueError,match='BLOCKED'): analyze(df,{'task':'ner'})
    c=analyze(df,{'task':'cluster','clusters':2}); assert len(c['assignments'])==4

def test_real_label_requirement_and_training_only_vocabulary():
    df=pd.DataFrame({'text':[f'skin lesion dermoscopy {i}' for i in range(12)]+[f'cardiac rhythm imaging {i}' for i in range(12)],'label':['skin']*12+['cardiac']*12})
    r=analyze(df,{'task':'classify'}); assert r['train_rows']==18; assert r['evaluation']['accuracy']>=.9
    with pytest.raises(ValueError): analyze(df.drop(columns='label'),{'task':'classify'})
