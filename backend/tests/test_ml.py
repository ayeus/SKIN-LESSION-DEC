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
