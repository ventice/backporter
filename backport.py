from typing import List, Optional
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from enum import Enum
import os
import subprocess

def run_merge():
    from argparse import ArgumentParser
    parser = ArgumentParser(
        prog='backport',
        description='Backport changes in C files'
    )
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('target')
    parser.add_argument('--log', action='store', default='hunks.json')
    args = parser.parse_args()
    merge(args.before, args.after, args.target)

@dataclass
class Chunk:
    begin: int
    end: int
    body: str

    def to_dict(self):
        return self.__dict__

@dataclass
class Hunk:
    source: Chunk
    destination: Chunk

    @property
    def id(self):
        return (self.source.begin, self.source.end)

    def to_dict(self):
        return json.dumps({
            'source': self.source.to_dict(),
            'destination': self.destination.to_dict()
        })


class MergeStatus(Enum):
    MERGED = 1
    REJECTED = 2

@dataclass
class MergedHunk:
    hunk: Hunk
    status: MergeStatus = MergeStatus.MERGED
    
    @property
    def id(self):
        return self.hunk.id

    def to_dict(self):
        return json.dumps({
            'status': self.status.name,
            'hunk': self.hunk.to_dict()
        })

class HunkSet:
    def get_hunks(self) -> List[Hunk]:
        raise NotImplementedError

class Rejection(HunkSet):
    pass

class Patch(HunkSet):
    def apply(self, target: str) -> Optional[Rejection]:
        raise NotImplementedError
    
class Merger:
    def __init__(self, before: str, after: str):
        self._before = before
        self._after = after

    def get_diff(self) -> Patch:
        raise NotImplementedError

class System:
    @staticmethod
    def run(command: str) -> subprocess.CompletedProcess:
        return subprocess.run(command, shell=True, capture_output=True)

    @staticmethod
    def diff(before: str, after: str, patch: str) -> subprocess.CompletedProcess:
        return System.run(f'diff {after} {before} > {patch}')

    @staticmethod
    def patch(target: str, patch: str, reject: str) -> subprocess.CompletedProcess:
        return System.run(f'patch -r {reject} {target} {patch}')

class SystemRejection(Rejection):
    def __init__(self, reject_file):
        self._file = reject_file

class SystemPatch(Patch):
    def __init__(self, patch_file: str, temp_dir: str):
        self._file = patch_file
        self._temp_dir = temp_dir
        self._applied = False

    def get_hunks(self) -> List[Hunk]:
        raise NotImplementedError

    def apply(self, target: str) -> Optional[Rejection]:
        if self._applied:
            return None
        self._applied = True
        reject_file = os.path.join(self._temp_dir, 'reject')
        result = System.patch(target, self._file, reject_file)
        if result.returncode == 0:
            return None
        if result.returncode == 1:
            return SystemRejection(reject_file)
        raise RuntimeError(f'Error occurred while patching the target: {result.stderr}') 

class SystemMerger(Merger):
    def __init__(self, before: str, after: str, temp_dir: str):
        super(SystemMerger, self).__init__(before, after)
        self._temp_dir = temp_dir

    def get_diff(self) -> Patch:
        import os
        patch_file = os.path.join(self._temp_dir, 'diff.patch')
        result = System.diff(self._before, self._after, patch_file)
        if result.returncode > 1:
            raise RuntimeError(f'Failed to compute difference between {self._before} and {self._after}')
        return SystemPatch(patch_file, self._temp_dir)

def merge(before: str, after: str, target: str) -> None:
    with TemporaryDirectory() as temp_dir:
        merger = SystemMerger(before, after, temp_dir)
        patch = merger.get_diff()
        #hunks = {hunk.id: hunk for hunk in patch.get_hunks()}
        reject = patch.apply(target)
        #if reject:
        #    rejected_hunks = {hunk.id for hunk in reject.get_hunks()}

if __name__ == '__main__':
    run_merge()

