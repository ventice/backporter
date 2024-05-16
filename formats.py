from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from re import compile as regex
from typing import List, Optional, Tuple, Dict

@dataclass
class Chunk:
    begin: int
    end: Optional[int] = None
    body: Optional[str] = None

    def to_dict(self):
        return self.__dict__

class ChangeType(Enum):
    CHANGED = 1
    ADDED = 2
    DELETED = 3

@dataclass
class Hunk:
    type: ChangeType
    source: Chunk
    destination: Chunk
    conflicts: Optional[Dict[int, Tuple[str, str]]] = None

    @property
    def id(self):
        return self.source.begin

    def to_dict(self):
        result = {
            'type': self.type.name,
            'rejected': bool(self.conflicts),
            'source': self.source and self.source.to_dict(),
            'destination': self.destination and self.destination.to_dict()
        }
        if self.conflicts:
            result['conflicts'] = self.conflicts
        return result


class FormatError(Exception):
    pass

class Context(ABC):
    def __init__(self, hunk: Hunk):
        self._hunk = hunk

    def process(self, line: str) -> bool:
        if not line.startswith(self._get_prefix()):
            return False
        self._get_chunk().body.append(line[2:])
        return True
    
    @abstractmethod
    def _get_prefix(self) -> str: pass

    @abstractmethod
    def _get_chunk(self) -> Chunk: pass

class ChangedContext(Context):
    def __init__(self, hunk: Hunk):
        super(ChangedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.CHANGED
        self._states = [(self._hunk.source, '<'), (self._hunk.destination, '>')]
        self._current_state = 0
        self._hunk.source.body = []
        self._hunk.destination.body = []

    def process(self, line: str) -> bool:
        if line.strip() == '---':
            if self._current_state == len(self._states) - 1:
                raise FormatError(f'Bad format of change hunk. Duplicate separator')
            self._current_state += 1
            return True
        return super(ChangedContext, self).process(line)

    def _get_prefix(self) -> str:
        return self._states[self._current_state][1]

    def _get_chunk(self) -> Chunk:
        return self._states[self._current_state][0]


class AddedContext(Context):
    def __init__(self, hunk: Hunk):
        super(AddedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.ADDED
        self._hunk.source.body = None
        self._hunk.destination.body = []

    def _get_prefix(self) -> str:
        return '>'

    def _get_chunk(self) -> Chunk:
        return self._hunk.destination

class DeletedContext(Context):
    def __init__(self, hunk: Hunk):
        super(DeletedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.DELETED
        self._hunk.source.body = []
        self._hunk.destination.body = None

    def _get_prefix(self) -> str:
        return '<'

    def _get_chunk(self) -> Chunk:
        return self._hunk.source


_CONTEXTS = {
    'c': ChangedContext,
    'a': AddedContext,
    'd': DeletedContext
}

def parse_hunk_header(groups: tuple) -> Hunk:
    result = Hunk(type=None, source=Chunk(begin=0), destination=Chunk(begin=0))
    source = list(map(int, groups[0].split(',')))
    if not (1 <= len(source) <= 2):
        raise FormatError(f'Source coordinates in bad format "{groups[0]}"')
    result.source.begin = source[0]
    result.source.end = source[1] if len(source) > 1 else result.source.begin

    dest = list(map(int, groups[2].split(',')))
    if not (1 <= len(dest) <= 2):
        raise FormatError(f'Destination coordinates in bad format "{groups[2]}"')
    result.destination.begin = dest[0]
    result.destination.end = dest[1] if len(dest) > 1 else result.destination.begin
    return result

_DIFF_HEADER_PATTERN = regex(r'^(\d+(?:,\d+)?)(\w)(\d+(?:,\d+)?)$')

def parse_diff(lines: List[str], contexts=_CONTEXTS) -> List[Hunk]:
    result:  List[Hunk] = []
    context: Context = None
    hunk: Hunk = None
    for line in lines:
        if context:
            if context.process(line):
                continue
            result.append(hunk)

        match = _DIFF_HEADER_PATTERN.match(line.strip())
        if not match:
            raise FormatError(f'Bad header format: "{line}"')

        hunk = parse_hunk_header(match.groups())
        context = contexts[match.group(2)](hunk)
    if hunk:
        result.append(hunk)
    return result    

def reject_hunk_separator(val: Optional[str], hunk: Hunk) -> Optional[Hunk]:
    return Hunk(ChangeType.CHANGED, Chunk(0), Chunk(0))

def reject_header(val: str, hunk: Hunk) -> Optional[Hunk]:
    nums = list(map(int, val.split(',')))
    if not (1 <= len(nums) <= 2):
        raise FormatError(f'Bad format of line numbers in header {val}')
    hunk.source.begin = nums[0]
    hunk.source.end = nums[1] if len(nums) > 1 else hunk.source.begin
    return None

def reject_chunk_separator(val: str, hunk: Hunk) -> Optional[Hunk]:
    nums = list(map(int, val.split(',')))
    if not (1 <= len(nums) <= 2):
        raise FormatError(f'Bad format of line numbers in separator {val}')
    hunk.destination.begin = nums[0]
    hunk.destination.end = nums[1] if len(nums) > 1 else hunk.destination.begin
    return None

def reject_source(val: str, hunk: Hunk) -> Optional[Hunk]:
    if not hunk.source.body:
        hunk.source.body = []
    hunk.source.body.append(val)
    return None

def reject_destination(val: str, hunk: Hunk) -> Optional[Hunk]:
    if not hunk.destination.body:
        hunk.destination.body = []
    hunk.destination.body.append(val)
    return None

_REJECT_GRAMMAR = [
    (regex(r'^\*{10,}$'), reject_hunk_separator),
    (regex(r'^\*{3} (\d+(?:,\d+)?)$'), reject_header),
    (regex(r'^-{3} (\d+(?:,\d+)?) -{5,}$'), reject_chunk_separator),
    (regex(r'^- (.*)$'), reject_source),
    (regex(r'^\+ (.*)$'), reject_destination)
]

def parse_reject(lines: List[str]) -> List[Hunk]:
    result = []
    hunk: Hunk = None

    for line in lines[2:]:
        for pattern, handler in _REJECT_GRAMMAR:
            if match := pattern.match(line.rstrip('\n')):
                new_hunk = handler(match.group(1) if match.groups() else None, hunk)
                if new_hunk:
                    if hunk:
                        result.append(hunk)
                    hunk = new_hunk
                break
        else:
            raise FormatError(f'Got unexpected line {line}')
    if hunk:
        result.append(hunk)
    return result
