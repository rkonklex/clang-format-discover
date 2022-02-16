import glob
import itertools
import os
import os.path
from typing import Iterable, List, Tuple, TypeVar

_T = TypeVar('T')


# based on https://stackoverflow.com/a/22045226
def chunkify(it: Iterable[_T], size: int) -> Iterable[Tuple[_T]]:
    it = iter(it)
    return iter(lambda: tuple(itertools.islice(it, size)), ())


def ordered_diff(first: Iterable[_T], second: Iterable[_T]) -> List[_T]:
    return [k for k in first if k not in second]


def search_files(roots: Iterable[str], extensions: List[str]) -> List[str]:
    def is_valid(filename: str) -> bool:
        _, ext = os.path.splitext(filename)
        return ext.lower() in extensions

    expanded_args = [path for globspec in roots for path in glob.glob(globspec, recursive=True)]
    file_list = [path for path in expanded_args if os.path.isfile(path)]
    for files in [walk_files(path) for path in expanded_args if os.path.isdir(path)]:
        file_list.extend(files)
    return [path for path in file_list if is_valid(path)]


def walk_files(dirpath: str) -> List[str]:
    return [os.path.join(root, name) for root, _, files in os.walk(dirpath) for name in files]
