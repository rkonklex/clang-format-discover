import concurrent.futures
import subprocess
from typing import Iterable, List


def capture_process_output(args: List[str], timeout: int=10) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout).stdout


class ThreadPoolProcessDispatcher(object):
    _executor: concurrent.futures.Executor

    def __init__(self, max_workers:int=5) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, *exc):
        return self._executor.__exit__(*exc)

    def map(self, args_list: Iterable[List[str]]) -> Iterable[Iterable[str]]:
        def dispatch_one(args: List[str]) -> Iterable[str]:
            return capture_process_output(args).splitlines()
        return self._executor.map(dispatch_one, args_list)
