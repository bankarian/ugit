"""A higher level module on top of data.
"""
import os
import itertools
import operator
import string

from collections import namedtuple, deque
from typing import Iterable, Dict, AnyStr
from . import data, diff

S = os.sep
Commit = namedtuple("Commit", ["tree", "parents", "message"])


def init():
    data.init()
    # Note that 'main' branch physically exists at the first commit
    data.update_ref("HEAD", data.RefValue(symbolic=True, value="refs/heads/main"))


def write_tree(directory="."):
    """
    Save a version of the directory in ugit object database,
    without addtional context.
    """
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f"{directory}/{entry.name}"
            if is_ignored(full):
                continue
            if entry.is_file(follow_symlinks=False):
                type_ = "blob"
                with open(full, "rb") as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = "tree"
                write_tree(full)
                oid = write_tree(full)
            entries.append((entry.name, oid, type_))
    tree = "".join(f"{type_} {oid} {name}\n" for name, oid, type_ in sorted(entries))
    # print(tree)
    return data.hash_object(tree.encode(), "tree")


def _empty_current_directory():
    for dirpath, dirnames, filenames in os.walk(".", topdown=False):
        # down to top
        for filename in filenames:
            path = os.path.relpath(f"{dirpath}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f"{dirpath}/{dirname}")
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
    tree = data.get_object(oid, "tree")
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(" ", 2)
        yield type_, oid, name


def get_tree(oid: str, base_path: str = "") -> Dict[str, AnyStr]:
    """
    Extract the whole tree recursively as a Dict.
    """
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        assert "/" not in name
        assert name not in ("..", ".")
        path = base_path + name
        if type_ == "blob":
            result[path] = oid
        elif type_ == "tree":
            result.update(get_tree(oid, f"{path}/"))
        else:
            assert False, f"Unknown tree entry {type_}"
    return result


def read_tree(tree_oid: str):
    """
    Empty current workspace, and restore a previous workspace
    from tree object.
    """
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data.get_object(oid))


def commit(message: str):
    """
    Copy current directory to object database with author and time,
    also save message as commit.
    """
    commit = f"tree {write_tree()}\n"
    HEAD = data.get_ref("HEAD").value
    if HEAD:
        commit += f"parent {HEAD}\n"
    MERGE_HEAD = data.get_ref("MERGE_HEAD").value
    if MERGE_HEAD:
        commit += f"parent {MERGE_HEAD}\n"
        data.delete_ref("MERGE_HEAD", deref=False)
    commit += "\n"
    commit += f"{message}\n"

    oid = data.hash_object(commit.encode(), "commit")
    data.update_ref("HEAD", value=data.RefValue(symbolic=False, value=oid), deref=True)

    return oid


def get_commit(oid: str) -> Commit:
    """
    Get commit(tree, parents, message) from object database.
    """
    parents = []
    commit = data.get_object(oid, "commit").decode()
    lines = iter(commit.splitlines())
    for line in itertools.takewhile(operator.truth, lines):
        # iteration stops when meets '\n'
        key, value = line.split(" ", 1)
        if key == "tree":
            tree = value
        elif key == "parent":
            parents.append(value)
        else:
            assert False, f"Unknown field {key}"

    message = "\n".join(lines)
    return Commit(tree=tree, parents=parents, message=message)


def checkout(name: str):
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree(commit.tree)
    if is_branch(name):
        HEAD = data.RefValue(symbolic=True, value=f"refs/heads/{name}")
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)

    data.update_ref("HEAD", HEAD, deref=False)


def is_branch(name: str) -> bool:
    return data.get_ref(f"refs/heads/{name}").value is not None


def create_tag(name: str, oid: str):
    data.update_ref(f"refs/tags/{name}", data.RefValue(symbolic=False, value=oid))


def get_oid(name: str) -> str:
    if name == "@":
        name = "HEAD"

    # Name is ref
    refs_to_try = [
        f"{name}",
        f"refs/{name}",
        f"refs/tags/{name}",
        f"refs/heads/{name}",
    ]
    for ref in refs_to_try:
        if data.get_ref(ref, deref=False).value:
            # if reference has value, return the ultimate value
            return data.get_ref(ref).value

    # Name is SHA1
    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    assert False, f"Unknown name {name}"


def iter_commits_and_parents(oids) -> Iterable[str]:
    """
    Iterate through the commit history from now to past.
    """
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft()
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        oids.extendleft(commit.parents[:1])
        oids.extend(commit.parents[1:])


def create_branch(name: str, oid: str):
    data.update_ref(f"refs/heads/{name}", data.RefValue(symbolic=False, value=oid))


def get_branch_name() -> str:
    """
    Return the branch name that HEAD points.
    Return None if HEAD is not symbolic.
    """
    HEAD = data.get_ref("HEAD", deref=False)
    if not HEAD.symbolic:
        # detached HEAD, dangerous!
        return None
    value = HEAD.value
    assert value.startswith("refs/heads/")
    return os.path.relpath(value, "refs/heads")


def iter_branch_names() -> Iterable[str]:
    for refname, _ in data.iter_refs(prefix=f"refs{S}heads/"):
        yield os.path.relpath(refname, f"refs{S}heads/")


def reset(oid: str):
    data.update_ref("HEAD", data.RefValue(symbolic=False, value=oid))


def get_working_tree():
    result = {}
    for root, _, filenames in os.walk("."):
        for filename in filenames:
            path = os.path.relpath(f"{root}/{filename}")
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                result[path] = data.hash_object(f.read())
    return result


def merge(other: str):
    HEAD = data.get_ref("HEAD").value
    assert HEAD
    merge_base = get_merge_base(other, HEAD)
    c_base = get_commit(merge_base)
    c_HEAD = get_commit(HEAD)
    c_other = get_commit(other)

    data.update_ref("MERGE_HEAD", data.RefValue(symbolic=False, value=other))

    read_tree_merged(c_HEAD.tree, c_other.tree, c_base.tree)
    print("Merged in working tree\nPlease commit")


def read_tree_merged(o_HEAD, o_other, o_base):
    _empty_current_directory()
    for path, blob in diff.merge_trees(
        get_tree(o_HEAD), get_tree(o_other), get_tree(o_base)
    ).items():
        os.makedirs(f"./{os.path.dirname(path)}", exist_ok=True)
        with open(path, "wb") as f:
            f.write(blob)


def get_merge_base(oid1: str, oid2: str) -> str:
    """
    Return the common ancester OID of two commits, None if no common ancestor.
    """
    parents1 = set(iter_commits_and_parents({oid1}))
    for oid in iter_commits_and_parents({oid2}):
        if oid in parents1:
            return oid


def is_ignored(path) -> bool:
    # TODO use '.ugitignore' file
    return ".ugit" in path.split(S) or ".git" in path.split(S) \
        or ".ugit" in path.split("/") or ".git" in path.split("/")
    
