"""Manage the disk related operation.
"""
import os
import hashlib

GIT_DIR = '.ugit'


S = os.sep


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}{S}objects")


def set_HEAD(oid: str):
    """
    Set the latest commit oid in HEAD
    """
    update_ref('HEAD', oid)


def get_HEAD():
    return get_ref('HEAD')



def update_ref(ref: str, oid: str):
    ref_path = f'{GIT_DIR}{S}{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(oid)


def get_ref(ref: str) -> str:
    ref_path = f'{GIT_DIR}{S}{ref}'
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            return f.read().strip()


def hash_object(data: bytes, type_='blob') -> str:
    """
    Content-addressable storage, save data to a new file with name of hash(data), return object id.
    The object structure: type00data
    """
    obj = type_.encode() + b'\x00' + data
    oid = hashlib.sha1(obj).hexdigest()
    path = f"{GIT_DIR}/objects/{oid}"

    with open(path, 'wb') as out:
        out.write(obj)
    return oid


def get_object(oid: str, expected='blob') -> bytes:
    """
    Get the file content by oid, note that the object type should meet the expected type.
    """
    with open(f"{GIT_DIR}/objects/{oid}", 'rb') as f:
        obj = f.read()
    type_, _, content = obj.partition(b'\x00')
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f'Expected {expected}, got {type_}'
    return content