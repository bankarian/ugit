"""A higher level module on top of data.
"""
import os
import itertools
import operator
import string

from collections import namedtuple, deque

from . import data

S = os.sep
Commit = namedtuple('Commit', ['tree', 'parent', 'message'])


def write_tree(directory='.'):
    """
    Save a version of the directory in ugit object database, 
    without addtional context.
    """
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f'{directory}{S}{entry.name}'
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


def _empty_current_directory():
    for dirpath, dirnames, filenames in os.walk('.', topdown=False):
        # down to top
        for filename in filenames:
            path = os.path.relpath(f'{dirpath}{S}{filename}')
            print(path)
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{dirpath}{S}{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # Deletion might fail if the directory contians ignored files,
                # so it's OK to pass
                pass


def _iter_tree_entries(oid: str):
    """
    Iterate through a level in tree and yield [type, oid, name] line by line.
    """
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid, name


def get_tree(oid: str, base_path: str = ''):
    """
    Extract the whole tree recursively as a map.
    """
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        assert '/' not in name
        assert name not in ('..', '.')
        path = base_path + name
        if type_ == 'blob':
            result[path] = oid
        elif type_ == 'tree':
            result.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown tree entry {type_}'
    return result


def read_tree(tree_oid: str):
    """
    Empty current workspace, and restore a previous workspace 
    from tree object.
    """
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))


def commit(message: str):
    """
    Copy current directory to object database with author and time, 
    also save message as commit.
    """
    commit = f'tree {write_tree()}\n'
    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD}\n'
    commit += '\n'
    commit += f'{message}\n'

    oid = data.hash_object(commit.encode(), 'commit')
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))

    return oid


def get_commit(oid: str) -> Commit:
    """
    Get commit(tree, parent, message) from object database.
    """
    parent = None
    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines())
    for line in itertools.takewhile(operator.truth, lines):
        # iteration stops when meets '\n'
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree = value
        elif key == 'parent':
            parent = value
        else:
            assert False, f'Unknown field {key}'

    message = '\n'.join(lines)
    return Commit(tree=tree, parent=parent, message=message)


def checkout(oid: str):
    commit = get_commit(oid)
    read_tree(commit.tree)
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))


def create_tag(name: str, oid: str):
    data.update_ref(f'refs{S}tags{S}{name}',
                    data.RefValue(symbolic=False, value=oid))


def get_oid(name: str) -> str:
    if name == '@':
        name = 'HEAD'

    # Name is ref
    refs_to_try = [
        f'{name}',
        f'refs{S}{name}',
        f'refs{S}tags{S}{name}',
        f'refs{S}heads{S}{name}',
    ]
    for ref in refs_to_try:
        r = data.get_ref(ref).value
        if r:
            return r

    # Name is SHA1
    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    assert False, f'Unknown name {name}'


def iter_commits_and_parents(oids):
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        oids.appendleft(commit.parent)


def create_branch(name: str, oid: str):
    data.update_ref(f'refs{S}heads{S}{name}', data.RefValue(symbolic=False, value=oid))


def is_ignored(path):
    # TODO use '.ugitignore' file
    return '.ugit' in path.split(S) or '.git' in path.split(S)