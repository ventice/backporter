from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import re
from abc import ABC, abstractmethod

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
    type: ChangeType = ChangeType.CHANGED,
    source: Chunk = Chunk(0, body=None)
    destination: Chunk = Chunk(0, body=None)

    @property
    def id(self):
        return tuple(filter(None, (self.source.begin, self.source.end)))

    def to_dict(self):
        return {
            'type': self.type.name,
            'source': self.source and self.source.to_dict(),
            'destination': self.destination and self.destination.to_dict()
        }


class FormatError(Exception):
    pass

_HEADER_PATTERN = re.compile(r'^(\d+(?:,\d+)?)(\w)(\d+(?:,\d+)?)$')

class Context(ABC):
    def __init__(self, hunk: Hunk):
        self._hunk = hunk

    @abstractmethod
    def process(self, line: str) -> bool:
        pass

class ChangedContext(Context):
    def __init__(self, hunk: Hunk):
        super(ChangedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.CHANGED
        self._states = [(self._hunk.source, '<'), (self._hunk.destination, '>')]
        self._current_state = 0

    def process(self, line: str) -> bool:
        state = self._states[self._current_state]
        if line.strip() == '---':
            if self._current_state == len(self._states) - 1:
                raise FormatError(f'Bad format of change hunk. Duplicate separator')
            self._current_state += 1
            return True
        elif not line.startswith(state[1]):
            return False
        state[0].body = state[0].body or []
        state[0].body.append(line[2:])
        return True

class AddedContext(Context):
    def __init__(self, hunk: Hunk):
        super(AddedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.ADDED
        self._hunk.source.body = None
        self._hunk.destination.body = []

    def process(self, line: str) -> bool:
        if not line.startswith('>'):
            return False
        self._hunk.destination.body.append(line[2:])
        return True

class DeletedContext(Context):
    def __init__(self, hunk: Hunk):
        super(DeletedContext, self).__init__(hunk)
        self._hunk.type = ChangeType.DELETED
        self._hunk.source.body = []
        self._hunk.destination.body = None

    def process(self, line: str) -> bool:
        if not line.startswith('<'):
            return False
        self._hunk.source.body.append(line[2:])
        return True


_CONTEXTS = {
    'c': ChangedContext,
    'a': AddedContext,
    'd': DeletedContext
}

def parse_hunk_header(groups: tuple) -> Hunk:
    result = Hunk()
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

def parse_diff(lines, contexts=_CONTEXTS) -> List[Hunk]:
    result:  List[Hunk] = []
    context: Context = None
    hunk: Hunk = None
    for line in lines:
        if context:
            if context.process(line):
                continue
            result.append(hunk)

        match = _HEADER_PATTERN.match(line)
        if not match:
            raise FormatError(f'Bad header format: "{line}"')

        hunk = parse_hunk_header(match.groups())
        context = contexts[match.group(2)](hunk)
    result.append(hunk)
    return result    


def parse_reject(lines) -> List[Hunk]:
    pass

