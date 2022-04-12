import os
import hashlib

GIT_DIR = '.ugit'

def init():
    os.makedirs(GIT_DIR)


def hash_object(data) -> str:
    oid = hashlib.sha1(data).hexdigest()
    with open(f"{GIT_DIR}/objects/{oid}", 'wb') as out:
        out.write(data)
    return oid