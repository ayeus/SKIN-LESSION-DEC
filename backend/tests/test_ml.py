import numpy as np
import pandas as pd
import pytest
import torch
from PIL import Image
from backend.app.services.ml import split_metadata,architecture,preprocessing

def test_group_split_no_leakage():
    df=pd.DataFrame([{'image_path':f'{label}-{g}-{j}.png','label':label,'group_id':f'{label}-{g}'} for label in ['a','b'] for g in range(10) for j in range(2)])
    train,val,test=split_metadata(df)
    assert len(train)+len(val)+len(test)==len(df)
    groups=[set(df.iloc[ix].group_id) for ix in (train,val,test)]
    assert not groups[0]&groups[1] and not groups[0]&groups[2] and not groups[1]&groups[2]
    with pytest.raises(ValueError): split_metadata(df.drop(columns='group_id'))

def test_tensor_preprocessing_and_eval_determinism():
    torch.manual_seed(42); m=architecture('small_cnn',3); m.eval()
    x=preprocessing()(Image.fromarray(np.full((64,80,3),128,np.uint8))).unsqueeze(0)
    assert x.shape==(1,3,224,224)
    with torch.no_grad(): a=m(x); b=m(x)
    assert a.shape==(1,3); torch.testing.assert_close(a,b,rtol=0,atol=0)

def test_actual_training_checkpoint_roundtrip_and_gradcam(tmp_path):
    """Explicitly synthetic artifact test; never used in app data or medical claims."""
    from backend.app.services.ml import train,load_artifact,predict,gradcam
    import json
    images=tmp_path/'images'; images.mkdir(); rows=[]
    for label in ('a','b'):
        for g in range(10):
            rgb=np.random.default_rng(g+(100 if label=='b' else 0)).integers(0,256,(32,32,3),dtype=np.uint8)
            name=f'{label}-{g}.png'; Image.fromarray(rgb).save(images/name)
            rows.append({'image_path':name,'label':label,'group_id':f'{label}-{g}'})
    metadata=tmp_path/'metadata.csv'; pd.DataFrame(rows).to_csv(metadata,index=False)
    output=tmp_path/'synthetic-artifact'; manifest=train(metadata,images,output,epochs=1,batch_size=4)
    assert (output/'weights.pt').is_file() and (output/'manifest.json').is_file()
    assert manifest['evaluation']['confusion_matrix'] and manifest['calibrated'] is False
    model,loaded=load_artifact(output); rgb=np.full((32,32,3),128,np.uint8)
    a=predict(rgb,output); b=predict(rgb,output); assert a==b
    assert sum(a['scores'].values())==pytest.approx(1,abs=1e-6)
    explanation=gradcam(rgb,output); assert explanation['overlay'].startswith('data:image/png;base64,')
    assert explanation['activation_peak']>=0
    with (output/'weights.pt').open('ab') as stream: stream.write(b'corrupted')
    with pytest.raises(ValueError,match='checksum'): load_artifact(output)
