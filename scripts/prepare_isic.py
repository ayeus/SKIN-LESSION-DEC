"""Validate actual ISIC2018 labels/grouping; safely extract images when downloaded."""
import json
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd
from backend.app.services.ml import split_metadata

def prepare(root=Path('data/raw/isic2018-task3')):
    groups=pd.read_csv(root/'ISIC2018_Task3_Training_LesionGroupings.csv')
    with ZipFile(root/'ISIC2018_Task3_Training_GroundTruth.zip') as archive:
        csvs=[p for p in archive.namelist() if p.endswith('.csv') and not p.startswith('__MACOSX/')]
        if len(csvs)!=1:raise ValueError('Expected one ground-truth CSV')
        with archive.open(csvs[0]) as stream:truth=pd.read_csv(stream)
    if groups.image.duplicated().any() or truth.image.duplicated().any():raise ValueError('Duplicate image IDs')
    classes=[c for c in truth if c!='image'];labels=truth[classes]
    if labels.isna().any().any() or not labels.isin([0,1]).all().all() or not (labels.sum(axis=1)==1).all():raise ValueError('Invalid one-hot clinical ground truth')
    merged=truth.merge(groups,on='image',how='outer',validate='one_to_one',indicator=True)
    if not (merged._merge=='both').all() or merged.lesion_id.isna().any():raise ValueError('Labels/grouping mismatch')
    metadata=pd.DataFrame({'image_path':truth.image+'.jpg','label':labels.idxmax(axis=1),'group_id':truth.image.map(groups.set_index('image').lesion_id)})
    train,val,test=split_metadata(metadata)
    archive_path=root/'ISIC2018_Task3_Training_Input.zip';images=root/'images'
    if archive_path.exists():
        images.mkdir(exist_ok=True)
        with ZipFile(archive_path) as archive:
            allowed=set(metadata.image_path);seen=set()
            for item in archive.infolist():
                name=Path(item.filename).name
                if name not in allowed:continue
                if name in seen:raise ValueError('Duplicate image basename in archive')
                seen.add(name)
                if item.file_size>20*1024*1024:raise ValueError('Oversized encoded image')
                destination=images/name
                if not destination.exists():
                    with archive.open(item) as src,destination.open('wb') as dst:
                        import shutil
                        shutil.copyfileobj(src,dst)
            if seen!=allowed:raise ValueError('Archive does not match image manifest')
    metadata.to_csv(root/'metadata.csv',index=False)
    missing=sum(not (images/name).is_file() for name in metadata.image_path)
    report={'source':'https://challenge.isic-archive.com/data/','license':'CC-BY-NC 4.0, official contributor attribution required','images_in_manifest':len(metadata),'lesion_groups':metadata.group_id.nunique(),'class_distribution':metadata.label.value_counts().to_dict(),'split_rows':{'train':len(train),'validation':len(val),'test':len(test)},'missing_images':missing,'group_semantics':'Lesion IDs only; same-patient leakage cannot be excluded. HAM10000 overlaps ISIC; do not merge as independent sources.','status':'Image files ready for full content checks' if not missing else 'Metadata validated; image acquisition incomplete; training BLOCKED'}
    (root/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report
if __name__=='__main__':prepare()
