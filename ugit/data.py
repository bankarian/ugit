'''
Manage the disk related operation.
'''
import os
import hashlib

GIT_DIR = '.ugit'


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}/objects")


def hash_object(data: bytes, type_='blob') -> str:
    '''
    Content-addressable storage, save data to a new file with name of hash(data), return object id.
    '''
    obj = type_.encode() + b'\x00' + data
    oid = hashlib.sha1(obj).hexdigest()
    path = f"{GIT_DIR}/objects/{oid}"

    with open(path, 'wb') as out:
        out.write(obj)
    return oid


def get_object(oid: str, expected='blob') -> bytes:
    '''
    Get the file content by oid.
    '''
    with open(f"{GIT_DIR}/objects/{oid}", 'rb') as f:
        obj = f.read()
    type_, _, content = obj.partition(b'\x00')
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f'Expected {expected}, got {type_}'
    return content