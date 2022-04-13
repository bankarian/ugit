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


def _empty_current_directory():
    for dirpath, dirnames, filenames in os.walk('.', topdown=False):
        # down to top
        for filename in filenames:
            path = os.path.relpath(f'{dirpath}/{filename}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{dirpath}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # Deletion might fail if the directory contians ignored files,
                # so it's OK to pass
                pass


def _iter_tree_entries(oid: str):
    '''
    Iterate through a level in tree and yield [type, oid, name] line by line.
    '''
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid,


def get_tree(oid: str, base_path: str = ''):
    '''
    Extract the whole tree recursively as a map.
    '''
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
    '''
    Empty current workspace, and restore a previous workspace
    from tree object.
    '''
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():
        os.makedirs(os.pardir.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))


def is_ignored(path):
    # TODO use '.ugitignore' file
    return '.ugit' in path.split('/') or '.git' in path.split('/')