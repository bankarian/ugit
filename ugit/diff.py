""" Module that deals with computing differences between objects.
"""

import subprocess
import os

from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp
from typing import Iterable, Dict, Tuple, AnyStr

from . import data


def compare_trees(*trees):
    """
    Take a list of trees, and return them as OIDs grouped by filename.
    """
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield (path, *oids)


def iter_changed_files(t_from, t_to) -> Iterable[Tuple[str, str]]:
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            action = "new file" if not o_from else "deleted" if not o_to else "modified"
            yield path, action


def diff_trees(t_from: Dict[str, str], t_to: Dict[str, str]):
    """
    Take two trees, compares them and return all entries that
    have differenct OIDs.
    """
    output = b""
    for (
            path,
            o_from,
            o_to,
    ) in compare_trees(t_from, t_to):
        if o_from != o_to:
            # output += f"changed: {path}\n"
            output += diff_blobs(o_from, o_to, path)
    return output


def diff_blobs(o_from, o_to, path="blob"):
    # TODO use `difflib` instead of Unix diff
    with Temp(delete=False) as f_from, Temp(delete=False) as f_to:
        for oid, f in ((o_from, f_from), (o_to, f_to)):
            if oid:
                f.write(data.get_object(oid))
                f.flush()
        with subprocess.Popen(
            [   "diff", "--unified",
                "--show-c-function",
                "--label", f"a/{path}", 
                f_from.name,
                "--label", f"b/{path}",
                f_to.name,
            ],
                stdout=subprocess.PIPE,
        ) as proc:
            output, _ = proc.communicate()
    # Mannually remove the tempfiles due to Windows file permission issues
    os.remove(f_from.name)
    os.remove(f_to.name)
    return output


def merge_trees(t_HEAD, t_other, t_base) -> Dict[str, AnyStr]:
    tree = {}
    for path, o_HEAD, o_other, o_base in compare_trees(t_HEAD, t_other, t_base):
        tree[path] = merge_blobs(o_HEAD, o_other, o_base)
    return tree


def merge_blobs(o_HEAD: str, o_other: str, o_base: str) -> AnyStr:
    """
    Return the merged content.
    """
    with Temp(delete=False) as f_HEAD, Temp(delete=False) as f_other,\
        Temp(delete=False) as f_base:
        for oid, f in ((o_HEAD, f_HEAD), (o_other, f_other), (o_base, f_base)):
            if oid:
                f.write(data.get_object(oid))
                f.flush()

        with subprocess.Popen(
            ['diff3', '-m',
                '-L', 'HEAD', f_HEAD.name,
                '-L', 'MERGE_HEAD', f_other.name,
                '-L', 'BASE', f_base.name,
            ], stdout=subprocess.PIPE) as proc:
            output, _ = proc.communicate()
            assert proc.returncode in (0, 1)

    os.remove(f_HEAD.name)
    os.remove(f_other.name)
    os.remove(f_base.name)
    return output
