""" Module that deals with computing differences between objects.
"""

from collections import defaultdict
from typing import Iterable, Dict


def compare_trees(*trees):
    """
    Take a list of trees, and return them grouped by filename.
    """
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid

    for path, oids in entries.items():
        yield (path, *oids)


def diff_trees(t_from: Dict[str, str], t_to: Dict[str, str]):
    """
    Take two trees, compares them and return all entries that
    have differenct OIDs.
    """
    output = ''
    for path, o_from, o_to, in compare_trees(t_from, t_to):
        if o_from != o_to:
            output += f'changed: {path}\n'
    return output