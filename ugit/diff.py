""" Module that deals with computing differences between objects.
"""

import subprocess
import os

from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp
from typing import Iterable, Dict, Tuple

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
            [
                "diff",
                "--unified",
                "--show-c-function",
                "--label",
                f"a/{path}",
                f_from.name,
                "--label",
                f"b/{path}",
                f_to.name,
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            output, _ = proc.communicate()
    # Mannually remove the tempfiles due to Windows file permission issues
    os.remove(f_from.name)
    os.remove(f_to.name)
    return output
