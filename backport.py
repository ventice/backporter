from argparse import ArgumentParser
from enum import Enum
from formats import Hunk
from typing import List, Dict, Tuple
import formats
import json
import os
import subprocess
import sys
import tempfile

class System:
    @staticmethod
    def diff(before: str, after: str) -> subprocess.CompletedProcess:
        return subprocess.run(f'diff {before} {after}', shell=True, capture_output=True)

    @staticmethod
    def patch(target: str, patch_data: bytes, reject: str) -> subprocess.CompletedProcess:
        pipe = subprocess.Popen(
            f'patch -f -r {reject} {target}',
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = pipe.communicate(input=patch_data)
        return subprocess.CompletedProcess(
            ['patch', '-f', '-r', reject, target],
            returncode=pipe.returncode,
            stdout=stdout,
            stderr=stderr
        )
    
    @staticmethod
    def read_lines(path: str) -> List[str]:
        with open(path) as f:
            return f.readlines()

def get_patch_hunks(patch_data: bytes) -> Dict[id, Hunk]:
    lines = patch_data.decode('utf-8').rstrip('\n').split('\n')
    return {hunk.id: hunk for hunk in formats.parse_diff(lines)}

def update_rejected_hunks(hunks: Dict[int, Hunk], reject_file: str):
    for hunk in formats.parse_reject(System.read_lines(reject_file)):
        hunks.setdefault(hunk.id, hunk).conflicts = get_conflicts(hunk)

def get_conflicts(hunk: Hunk) -> Dict[int, Tuple[str, str]]:
    lines = {i: l for i, l in zip(range(hunk.destination.begin, hunk.destination.end + 1), hunk.destination.body)}
    return {
        i: (l, lines.get(i))
        for i, l in zip(range(hunk.source.begin, hunk.source.end + 1), hunk.source.body)
            if l != lines.get(i)
    }

def merge(before: str, after: str, target: str) -> Dict[int, Hunk]:
    with tempfile.TemporaryDirectory() as temp_dir:
        hunks = None
    
        diff = System.diff(before, after)
        if diff.returncode > 1:
            raise RuntimeError(f'Failed to compute difference between {before} and {after}')
        patch_data = diff.stdout
        hunks = get_patch_hunks(patch_data)

        reject_file = os.path.join(temp_dir, 'reject')
        patch = System.patch(target, patch_data, reject_file)
        if patch.returncode == 2:
            raise RuntimeError(f'Error occurred while patching the target: {patch.stderr}') 

        if patch.returncode == 1:
            update_rejected_hunks(hunks, reject_file)
        
        return hunks 

def get_log(before: str, after: str, target: str, hunks: List[Hunk]) -> Dict:
    return {
        'before': before,
        'after': after,
        'target': target,
        'hunks': [hunk.to_dict() for hunk in hunks]
    }
    
class ExitCodes(Enum):
    SUCCESS = 0
    BAD_ARGUMENT = 1
    RUNTIME_ERROR = 2

def ensure_existing_file(path: str):
    if not os.path.isfile(path):
        raise ValueError(f'The path "{path}" does not designate an existing file')

def run_merge():
    parser = ArgumentParser(
        prog='backport',
        description='Backport changes in C files. The tool computes the difference between the files ' 
        '<before> and <after> and merges them into the file designated by <target>. If --log option is '
        'specified the detailed information on merged and conflicting hunks is additionally written to '
        'the provided file in JSON format.'
    )
    parser.add_argument('before', help='The original file path')
    parser.add_argument('after', help='The file containing the changes to be backported')
    parser.add_argument('target', help='The file to incorporate the changes into')
    parser.add_argument('-l', '--log', action='store', dest='log_file', help='The path of the JSON file to write the operations into.')
    args = parser.parse_args()
    try:
        for path in (args.before, args.after, args.target):
           ensure_existing_file(path)
    except ValueError as e:
        sys.stderr.write(f'ERROR: {e.args[0]}\n')
        sys.exit(ExitCodes.BAD_ARGUMENT.value)

    try:
        hunks = merge(args.before, args.after, args.target)
        if args.log_file:
            with open(args.log_file, 'w') as f:
                log = get_log(args.before, args.after, args.target, sorted(hunks.values(), key=lambda h: h.id))
                f.write(json.dumps(log, indent=2))

    except Exception as e:
        sys.stderr.write(f'ERROR: {e.args[0]}\n')
        sys.exit(ExitCodes.RUNTIME_ERROR.value)

if __name__ == '__main__':
    run_merge()
