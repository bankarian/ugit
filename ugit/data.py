"""Manage the disk related operation.
"""
import os
import hashlib

from collections import namedtuple
from typing import Iterable, Tuple

GIT_DIR = ".ugit"


def init():
    """
    Initialize '.ugit' directory
    """
    os.makedirs(GIT_DIR)
    os.makedirs(f"{GIT_DIR}/objects")


RefValue = namedtuple("RefValue", ["symbolic", "value"])


def update_ref(ref: str, value: RefValue, deref: bool = True):
    """
    Update reference, dereference by default.
    """
    ref = _get_ref_internal(ref, deref)[0]

    assert value.value
    if value.symbolic:
        val = f"ref: {value.value}"
    else:
        val = value.value

    ref_path = f"{GIT_DIR}/{ref}"
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w") as f:
        f.write(val)


def get_ref(ref: str, deref: bool = True) -> RefValue:
    """
    Get reference value, which is oid, dereference by default. Return None if no such reference.
    """
    return _get_ref_internal(ref, deref)[1]


def _get_ref_internal(ref: str, deref: bool) -> Tuple[str, RefValue]:
    """
    Dereference and get the last non-symbolic ref, which points directly to a commit
    """
    ref_path = f"{GIT_DIR}/{ref}"
    value = None
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            value = f.read().strip()

    is_symbolic = bool(value) and value.startswith("ref:")
    if is_symbolic:
        value = value.split(":", 1)[1].strip()
        if deref:
            # dereference recursively
            return _get_ref_internal(value, deref=True)

    return ref, RefValue(symbolic=is_symbolic, value=value)


def hash_object(data: bytes, type_="blob") -> str:
    """
    Content-addressable storage, save data to a new file with name of hash(data), return object id.
    The object structure: type00data
    """
    obj = type_.encode() + b"\x00" + data
    oid = hashlib.sha1(obj).hexdigest()
    path = f"{GIT_DIR}/objects/{oid}"

    with open(path, "wb") as out:
        out.write(obj)
    return oid


def get_object(oid: str, expected="blob") -> bytes:
    """
    Get the file content by oid, note that the object type should meet the expected type.
    """
    with open(f"{GIT_DIR}/objects/{oid}", "rb") as f:
        obj = f.read()
    type_, _, content = obj.partition(b"\x00")
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f"Expected {expected}, got {type_}"
    return content


def iter_refs(prefix: str = "", deref: bool = True) -> Iterable[Tuple[str, RefValue]]:
    """
    A generator that iterates all refs and yields (refname, refcontent)
    """
    refs = ["HEAD"]
    for root, _, filenames in os.walk(f"{GIT_DIR}/refs/"):
        root = os.path.relpath(root, GIT_DIR)
        refs.extend(f"{root}/{name}" for name in filenames)

    for refname in refs:
        if not refname.startswith(prefix):
            continue
        yield refname, get_ref(refname, deref)
