"""Disposable real API/storage for browser tests; never binds working research data."""
import os
import subprocess
import sys
import tempfile

if __name__=='__main__':
    if os.getenv('DERMA_E2E')!='1':raise SystemExit('Browser API requires explicit isolated-test environment')
    with tempfile.TemporaryDirectory(prefix='derma-browser-tests-') as directory:
        os.environ['DERMA_STORAGE']=directory
        os.environ['DATABASE_URL']='sqlite:///'+directory+'/research.db'
        os.environ.pop('DERMA_MODEL_DIR',None);os.environ.pop('DERMA_NER_MODEL',None)
        os.environ['DERMA_LESION_METADATA']=directory+'/no-lesion-data.csv'
        os.environ['DERMA_LESION_IMAGES']=directory+'/no-lesion-images'
        subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],check=True)
        import uvicorn
        uvicorn.run('backend.app.main:app',host='127.0.0.1',port=18400,log_level='warning')
