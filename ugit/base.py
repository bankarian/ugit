'''
A higher level module on top of data.
'''
import os
from . import data


def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f'{directory}/{entry.name}'
            if is_ignored(full):
                continue
            if entry.is_file(follow_symlinks=False):
                type_ = 'blob'
                with open(full, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = 'tree'
                write_tree(full)
                oid = write_tree(full)
            entries.append((entry.name, oid, type_))
    tree = ''.join(f'{type_} {oid} {name}\n'
                   for name, oid, type_ in sorted(entries))
    # print(tree)
    return data.hash_object(tree.encode(), 'tree')


def is_ignored(path):
    # TODO use '.ugitignore' file
    return '.ugit' in path.split('/') or '.git' in path.split('/')