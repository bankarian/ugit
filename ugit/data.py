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
    """
    Get oid from reference, which is a tag assigned by the user.
    """
    ref_path = f'{GIT_DIR}{S}{ref}'
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            return f.read().strip()
    assert False, f'Unknown ref: {ref}'


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


def iter_refs():
    """
    A generator that iterates all refs and yields (refname, refcontent)
    """
    refs = ['HEAD']
    for root, _, filenames in os.walk(f'{GIT_DIR}{S}refs{S}'):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}{S}{name}' for name in filenames)

    for refname in refs:
        yield refname, get_ref(refname)