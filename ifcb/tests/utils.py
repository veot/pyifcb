import hashlib
import os
import random
import shutil
import tempfile
from contextlib import contextmanager
from functools import wraps

@contextmanager
def test_dir():
    """context mgr for tempdir"""
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        shutil.rmtree(d)
        
@contextmanager
def test_file(name=None):
    if name is None:
        name = 'pyifcb_' + hashlib.sha1(random.getrandbits(64).to_bytes(8, 'little')).hexdigest()
    with test_dir() as d:
        yield os.path.join(d, name)
    
def withfile(method):
    """decorator that adds a named temporary file argument"""
    @wraps(method)
    def wrapper(*args, **kw):
        with test_file() as f:
            args = args + (f,)
            return method(*args, **kw)
    return wrapper

