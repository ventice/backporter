import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from unittest.mock import Mock
from formats import Hunk, Chunk, ChangeType

def test_id_is_source_begin():
    hunk = Hunk(type=ChangeType.CHANGED, source=Chunk(begin=1, end=2), destination=Chunk(begin=3, end=4))
    assert hunk.id == 1

def test_converts_to_dict():
    hunk = Hunk(
        type=ChangeType.CHANGED,
        source=Chunk(
            begin=1,
            end=2,
            body=['hello', 'world']
        ),
        destination=Chunk(
            begin=3,
            end=4,
            body=['salut', 'monde']
        )
    )
    assert hunk.to_dict() == {
        'type': 'CHANGED',
        'source': {
            'begin': 1,
            'end': 2,
            'body': ['hello', 'world']
        },
        'destination': {
            'begin': 3,
            'end': 4,
            'body': ['salut', 'monde']
        },
    }
