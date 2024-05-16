from pathlib import Path
import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from formats import Hunk, Chunk, ChangeType
from unittest.mock import Mock

def test_id_is_source_begin():
    hunk = Hunk(type=ChangeType.CHANGED, source=Chunk(begin=1, end=2), destination=Chunk(begin=3, end=4))
    assert hunk.id == 1

def test_converts_accepted_hunk_as_not_rejected():
    hunk = Hunk(
        type=ChangeType.CHANGED,
        conflicts={1: ('hello', 'hello!')},
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
        'rejected': True,
        'conflicts': {1: ('hello', 'hello!')},
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

def test_skips_conflicts_if_none():
    hunk = Hunk(
        type=ChangeType.CHANGED,
        conflicts=None,
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
        'rejected': False,
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
