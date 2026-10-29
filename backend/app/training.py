"""Server-controlled experiment paths; no arbitrary artifact upload or promotion."""
import json
import os
from pathlib import Path
from .db import ROOT


def source_paths():
    root=ROOT/'raw/isic2018-task3'
    return Path(os.getenv('DERMA_LESION_METADATA',str(root/'metadata.csv'))),Path(os.getenv('DERMA_LESION_IMAGES',str(root/'images')))


def readiness():
    metadata,images=source_paths()
    if not metadata.is_file(): return {'ready':False,'reason':'Labeled image metadata is not available'}
    import pandas as pd
    from .services.ml import split_metadata
    try:
        frame=pd.read_csv(metadata,dtype={'label':str,'group_id':str}); split_metadata(frame)
        missing=0
        for value in frame.image_path:
            path=(images/value).resolve()
            if not path.is_relative_to(images.resolve()):raise ValueError('Image path escapes configured dataset')
            missing+=not path.is_file()
        return {'ready':missing==0,'manifest_rows':len(frame),'missing_images':missing,'classes':sorted(frame.label.unique().tolist()),
                'reason':'All manifest files exist; full content/leakage checks occur before training' if not missing else 'Image download/extraction is incomplete',
                'grouping_limit':'Group IDs must represent patients where available. Lesion-only groups cannot rule out same-patient leakage.'}
    except (ValueError,KeyError,OSError) as error:return {'ready':False,'reason':str(error)}


def artifact_dir(run_id):return ROOT/'models'/run_id


def selected_directory():
    configured=os.getenv('DERMA_MODEL_DIR')
    if configured:return Path(configured)
    pointer=ROOT/'model-selection.json'
    if not pointer.exists():return None
    try:
        id=json.loads(pointer.read_text())['training_run_id']
        from uuid import UUID
        UUID(id)
        return artifact_dir(id)
    except (ValueError,KeyError):return None


def select_artifact(run_id):
    from .services.ml import load_artifact
    _,manifest=load_artifact(artifact_dir(run_id))
    path=ROOT/'model-selection.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'training_run_id':run_id,'weights_sha256':manifest['weights_sha256']}));temporary.replace(path)
    return {'training_run_id':run_id,'weights_sha256':manifest['weights_sha256'],'research_only':True,'clinical_validation':'Not established'}
