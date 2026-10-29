"""Synthetic algorithm fixtures only; never clinical validation."""
import os
import tempfile
os.environ['DERMA_STORAGE']=tempfile.mkdtemp(prefix='derma-tests-')
os.environ['DERMA_API_TOKEN']='synthetic-test-token-not-a-secret'
os.environ['DERMA_DEV_CREATE_SCHEMA']='1'
