from typing import List, Optional, Dict
from tempfile import TemporaryDirectory
from dataclasses import dataclass
import os
import subprocess
from formats import Hunk
import formats

@dataclass
class Conflict:
    source: str
    destination: str

@dataclass
class RejectedHunk:
    hunk: Hunk
    conflicts: Dict[int, Conflict]
    
    @property
    def id(self):
        return self.hunk.id

    def to_dict(self):
        return {
            'status': 'CONFLICT',
            'hunk': self.hunk.to_dict(),
            'conficts': [
                {
                    'line': line,
                    'source': conflict.source,
                    'destination': conflict.destination
                }
                for line, conflict in self.conflicts.items()
            ]
        }

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
        return System.run(f'diff {before} {after} > {patch}')

    @staticmethod
    def patch(target: str, patch: str, reject: str) -> subprocess.CompletedProcess:
        return System.run(f'patch -f -r {reject} {target} {patch}')
    
    @staticmethod
    def read(path: str) -> List[str]:
        with open(path) as f:
            return f.readlines()

class SystemRejection(Rejection):
    def __init__(self, reject_file):
        self._file = reject_file

    def get_hunks(self) -> List[Hunk]:
        lines = System.read(self._file)
        return formats.parse_reject(lines)

class SystemPatch(Patch):
    def __init__(self, patch_file: str, temp_dir: str):
        self._file = patch_file
        self._temp_dir = temp_dir
        self._applied = False

    def get_hunks(self) -> List[Hunk]:
        lines = System.read(self._file)
        return formats.parse_diff(lines)

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

class HunkProcessor:
    def process_diff(self, hunks: HunkSet): pass

    def process_reject(self, hunks: HunkSet): pass

    def finalize(self): pass

def merge(before: str, after: str, target: str, processor: HunkProcessor = HunkProcessor()) -> None:
    with TemporaryDirectory() as temp_dir:
        merger = SystemMerger(before, after, temp_dir)
        patch = merger.get_diff()
        processor.process_diff(patch)
        reject = patch.apply(target)
        if reject:
            processor.process_reject(reject)
        processor.finalize()

class JsonLogger(HunkProcessor):
    def __init__(self, log, before, after, target):
        self._log = log
        self._before = before
        self._after = after
        self._target = target
        self._hunks = {}

    def process_diff(self, hunks: HunkSet):
        self._hunks = {hunk.id: hunk for hunk in hunks.get_hunks()}

    def process_reject(self, hunks: HunkSet):
        target_lines = {no: line for no, line in enumerate(System.read(self._target))}
        for hunk in hunks.get_hunks():
            self._hunks[hunk.id] = RejectedHunk(hunk, self._get_conflicts(hunk, target_lines))

    def finalize(self):
        import json
        with open(self._log, 'w') as f:
            f.write(json.dumps(self._get_log(), indent=2))

    def _get_conflicts(self, hunk: Hunk, lines: Dict[int, str]) -> Dict[int, Conflict]:
        return {
            i: Conflict(l, lines[i])
            for i, l in zip(range(hunk.source.begin, hunk.source.end + 1), hunk.source.body)
        }

    def _get_log(self) -> Dict:
        return {
            'before': self._before,
            'after': self._after,
            'target': self._target,
            'hunks': [hunk.to_dict() for hunk in self._hunks.values()]
        }

def run_merge():
    from argparse import ArgumentParser
    parser = ArgumentParser(
        prog='backport',
        description='Backport changes in C files'
    )
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('target')
    parser.add_argument('--log', action='store', dest='log_file', default=None)
    args = parser.parse_args()
    logger = JsonLogger(args.log_file, args.before, args.after, args.target) if args.log_file else HunkProcessor()

    merge(args.before, args.after, args.target, logger)

if __name__ == '__main__':
    run_merge()

