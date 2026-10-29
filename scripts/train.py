"""Run from project root: python -m scripts.train --help"""
import argparse
from pathlib import Path
from backend.app.services.ml import train
p=argparse.ArgumentParser()
p.add_argument('--metadata',type=Path,required=True); p.add_argument('--images',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
p.add_argument('--architecture',choices=['small_cnn','resnet18','efficientnet_b0'],default='small_cnn'); p.add_argument('--epochs',type=int,default=5); p.add_argument('--batch-size',type=int,default=16)
p.add_argument('--pretrained',action='store_true',help='Explicitly authorize torchvision ImageNet weight download; not a lesion-trained model')
a=p.parse_args(); train(a.metadata,a.images,a.output,a.architecture,a.epochs,a.batch_size,pretrained=a.pretrained)
