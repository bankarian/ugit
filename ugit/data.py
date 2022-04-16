"""Manage the disk related operation.
"""
import os
import hashlib

from collections import namedtuple
from typing import Iterable

GIT_DIR = '.ugit'


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}/objects")


RefValue = namedtuple('RefValue', ['symbolic', 'value'])


def update_ref(ref: str, value: RefValue):
    assert not value.symbolic
    ref = _get_ref_internal(ref)[0]
    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(value.value)


def get_ref(ref: str) -> RefValue:
    """
    Get oid from reference, which is a tag assigned by the user.
    """
    return _get_ref_internal(ref)[1]


def _get_ref_internal(ref: str) -> tuple[str, RefValue]:
    """
    Dereference and get the last non-symbolic ref, which points directly to a commit
    """
    ref_path = f'{GIT_DIR}/{ref}'
    value = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()

    is_symbolic = bool(value) and value.startswith('ref:')
    if is_symbolic:
        value = value.split(':', 1)[1].strip()
        return _get_ref_internal(value)

    return ref, RefValue(symbolic=False, value=value)


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


def iter_refs() -> Iterable[tuple[str, RefValue]]:
    """
    A generator that iterates all refs and yields (refname, refcontent)
    """
    refs = ['HEAD']
    for root, _, filenames in os.walk(f'{GIT_DIR}/refs/'):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f'{root}/{name}' for name in filenames)

    for refname in refs:
        yield refname, get_ref(refname)