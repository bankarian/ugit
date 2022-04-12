import os
import hashlib

GIT_DIR = '.ugit'

def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}/objects")


def hash_object(data) -> str:
    '''
    Content-addressable storage, save data to a new file with name of hash(data), return object id.
    '''
    oid = hashlib.sha1(data).hexdigest()
    path = f"{GIT_DIR}/objects/{oid}"
    
    with open(path, 'wb') as out:
        out.write(data)
    return oid

def get_object(oid: str):
    with open(f"{GIT_DIR}/objects/{oid}", 'rb') as f:
        return f.read()