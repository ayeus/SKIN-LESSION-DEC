"""Actual CNN training. No downloads, prediction defaults, or clinical efficacy claims."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image, ImageOps
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, roc_auc_score, log_loss

SIZE=224
MEAN=[.485,.456,.406]; STD=[.229,.224,.225]

def preprocessing(training=False):
    steps=[transforms.Resize((SIZE,SIZE))]
    if training: steps += [transforms.RandomHorizontalFlip(),transforms.RandomRotation(15)]
    return transforms.Compose(steps+[transforms.ToTensor(),transforms.Normalize(MEAN,STD)])

def split_metadata(df,seed=42):
    required={'image_path','label','group_id'}
    if not required<=set(df): raise ValueError('Metadata requires image_path,label,group_id')
    if df[list(required)].isna().any().any(): raise ValueError('Metadata has missing values')
    if df.image_path.duplicated().any(): raise ValueError('Image paths must be unique')
    if df.label.nunique()<2: raise ValueError('At least two real classes required')
    if df.groupby('label').group_id.nunique().min()<5: raise ValueError('At least five independent groups per class required for five-fold stratified group split')
    folds=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=seed).split(df,df.label,df.group_id))
    test=folds[0][1]; val=folds[1][1]; train=np.setdiff1d(np.arange(len(df)),np.r_[test,val])
    groups=[set(df.iloc[ix].group_id) for ix in (train,val,test)]
    if any(groups[i]&groups[j] for i,j in ((0,1),(0,2),(1,2))): raise ValueError('Group leakage detected')
    if any(set(df.iloc[ix].label)!=set(df.label) for ix in (train,val,test)): raise ValueError('Split lacks classes; provide more independent groups')
    return train,val,test

def architecture(name,classes,pretrained=False):
    if name=='resnet18':
        model=models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None); model.fc=nn.Linear(model.fc.in_features,classes)
    elif name=='efficientnet_b0':
        model=models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT if pretrained else None); model.classifier[1]=nn.Linear(model.classifier[1].in_features,classes)
    elif name=='small_cnn':
        model=nn.Sequential(nn.Conv2d(3,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(16,32,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d(1),nn.Flatten(),nn.Linear(32,classes))
    else: raise ValueError('Supported architectures: small_cnn, resnet18, efficientnet_b0')
    return model

class Lesions(Dataset):
    def __init__(self,df,root,labels,training): self.df=df; self.root=root.resolve(); self.labels=labels; self.transform=preprocessing(training)
    def __len__(self): return len(self.df)
    def __getitem__(self,i):
        row=self.df.iloc[i]; path=(self.root/row.image_path).resolve()
        if not path.is_relative_to(self.root): raise ValueError('Image path escapes dataset root')
        with Image.open(path) as im: image=ImageOps.exif_transpose(im).convert('RGB'); tensor=self.transform(image)
        return tensor,self.labels.index(str(row.label))

def train(metadata,images,output,name='small_cnn',epochs=5,batch_size=16,seed=42,pretrained=False):
    if not 1<=epochs<=1000 or not 1<=batch_size<=128: raise ValueError('Invalid epochs/batch size')
    torch.manual_seed(seed); np.random.seed(seed); torch.use_deterministic_algorithms(True)
    df=pd.read_csv(metadata,dtype={'label':str,'group_id':str}); train_ix,val_ix,test_ix=split_metadata(df,seed)
    # Detect identical image bytes across groups before training.
    hashes={}
    for _,row in df.iterrows():
        path=(images/row.image_path).resolve()
        if not path.is_relative_to(images.resolve()): raise ValueError('Path traversal in manifest')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes and hashes[digest]!=row.group_id: raise ValueError('Identical image bytes across different groups')
        hashes[digest]=row.group_id
    labels=sorted(df.label.unique()); model=architecture(name,len(labels),pretrained)
    loaders=[DataLoader(Lesions(df.iloc[ix],images,labels,i==0),batch_size=batch_size,shuffle=i==0,num_workers=0) for i,ix in enumerate((train_ix,val_ix,test_ix))]
    counts=df.iloc[train_ix].label.value_counts(); weights=torch.tensor([len(train_ix)/(len(labels)*counts[c]) for c in labels],dtype=torch.float32)
    loss_fn=nn.CrossEntropyLoss(weight=weights); optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    output.mkdir(parents=True,exist_ok=False); best=float('inf'); history=[]
    for epoch in range(epochs):
        totals=[]
        for phase,loader in enumerate(loaders[:2]):
            model.train(phase==0); loss_sum=0.; correct=0; n=0
            with torch.set_grad_enabled(phase==0):
                for x,y in loader:
                    logits=model(x); loss=loss_fn(logits,y)
                    if phase==0: optimizer.zero_grad(); loss.backward(); optimizer.step()
                    loss_sum+=loss.item()*len(y); correct+=(logits.argmax(1)==y).sum().item(); n+=len(y)
            totals.append({'loss':loss_sum/n,'accuracy':correct/n})
        history.append({'epoch':epoch+1,'train':totals[0],'validation':totals[1]})
        if totals[1]['loss']<best:
            best=totals[1]['loss']; torch.save(model.state_dict(),output/'weights.pt')
        (output/'history.json').write_text(json.dumps(history,indent=2))
    model.load_state_dict(torch.load(output/'weights.pt',weights_only=True)); model.eval(); truth=[]; scores=[]
    with torch.no_grad():
        for x,y in loaders[2]: truth+=y.tolist(); scores+=model(x).softmax(1).tolist()
    scores=np.asarray(scores); pred=scores.argmax(1)
    evaluation={'classification':classification_report(truth,pred,labels=list(range(len(labels))),target_names=labels,output_dict=True,zero_division=0),
        'balanced_accuracy':balanced_accuracy_score(truth,pred),'confusion_matrix':confusion_matrix(truth,pred,labels=list(range(len(labels)))).tolist(),
        'log_loss':log_loss(truth,scores,labels=list(range(len(labels)))),'brier_multiclass':float(np.mean(np.sum((scores-np.eye(len(labels))[truth])**2,axis=1))),
        'roc_auc':roc_auc_score(truth,scores[:,1]) if len(labels)==2 else roc_auc_score(truth,scores,multi_class='ovr',labels=list(range(len(labels))))}
    manifest={'architecture':name,'labels':labels,'size':SIZE,'mean':MEAN,'std':STD,'seed':seed,'epochs':epochs,'pretrained_imagenet':pretrained,
        'metadata_sha256':hashlib.sha256(metadata.read_bytes()).hexdigest(),'weights_sha256':hashlib.sha256((output/'weights.pt').read_bytes()).hexdigest(),
        'split_indices':{'train':train_ix.tolist(),'validation':val_ix.tolist(),'test':test_ix.tolist()},
        'group_semantics':'Owner must document patient vs lesion grouping; lesion IDs do not exclude same-patient leakage.',
        'calibrated':False,'research_only':True,'evaluation':evaluation}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)); return manifest

def load_artifact(root):
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest.get('research_only') is not True or manifest.get('calibrated') is not False: raise ValueError('Unsupported artifact safety metadata')
    if manifest.get('size')!=SIZE or manifest.get('mean')!=MEAN or manifest.get('std')!=STD: raise ValueError('Artifact preprocessing mismatch')
    weights=root/'weights.pt'
    if hashlib.sha256(weights.read_bytes()).hexdigest()!=manifest.get('weights_sha256'): raise ValueError('Model checksum mismatch')
    model=architecture(manifest['architecture'],len(manifest['labels'])); model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True)); model.eval()
    return model,manifest

def predict(rgb,root):
    model,manifest=load_artifact(root); x=preprocessing()(Image.fromarray(rgb)).unsqueeze(0)
    with torch.no_grad(): scores=model(x).softmax(1)[0].tolist()
    return {'scores':dict(zip(manifest['labels'],scores)),'research_prediction':manifest['labels'][int(np.argmax(scores))],
        'calibrated':False,'model_sha256':manifest['weights_sha256'],'limitation':'Uncalibrated research scores, not diagnostic confidence. External clinical validation has not been established.'}
