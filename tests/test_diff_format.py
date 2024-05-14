import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from unittest.mock import Mock
import formats

def test_parse_hunk_header():
    hunk = formats.parse_hunk_header(('2', 'c', '2,5'))
    assert hunk.source.begin == 2
    assert hunk.source.end == 2
    assert hunk.destination.begin == 2
    assert hunk.destination.end == 5

    hunk = formats.parse_hunk_header(('1,4', 'd', '0'))
    assert hunk.source.begin == 1
    assert hunk.source.end == 4
    assert hunk.destination.begin == 0
    assert hunk.destination.end == 0

    hunk = formats.parse_hunk_header(('7', 'a', '7'))
    assert hunk.source.begin == 7
    assert hunk.source.end == 7
    assert hunk.destination.begin == 7
    assert hunk.destination.end == 7

def test_parses_change():
    hunk = formats.Hunk(None, formats.Chunk(None), formats.Chunk(None))
    context = formats.ChangedContext(hunk)
    assert hunk.type == formats.ChangeType.CHANGED
    assert context.process('< Hello')
    assert context.process('< World')
    assert context.process('---')
    assert context.process('> Salut')
    assert context.process('> Monde')
    assert not context.process('garbage')
    assert hunk.source.body == ['Hello', 'World']
    assert hunk.destination.body == ['Salut', 'Monde']

def test_throws_when_double_separator():
    hunk = formats.Hunk(None, formats.Chunk(None), formats.Chunk(None))
    context = formats.ChangedContext(hunk)
    assert context.process('---')
    assert context.process('> Hello')
    with pytest.raises(formats.FormatError):
        context.process('---')

def test_parses_addition():
    hunk = formats.Hunk(None, formats.Chunk(None), formats.Chunk(None))
    context = formats.AddedContext(hunk)
    assert hunk.type == formats.ChangeType.ADDED
    assert context.process('> Hello')
    assert context.process('> World')
    assert not context.process('garbage')
    assert hunk.source.body is None
    assert hunk.destination.body == ['Hello', 'World']

def test_parses_deletion():
    hunk = formats.Hunk(None, formats.Chunk(None), formats.Chunk(None))
    context = formats.DeletedContext(hunk)
    assert hunk.type == formats.ChangeType.DELETED
    assert context.process('< Hello')
    assert context.process('< World')
    assert not context.process('garbage')
    assert hunk.source.body == ['Hello', 'World']
    assert hunk.destination.body is None


def test_parse_passes_abbreviation_to_corresponding_context():
    context = Mock(process=Mock(return_value=True))
    contexts = {'c': Mock(return_value=context)}
    formats.parse_diff(['1,2c3,4', 'hello', 'world'], contexts)
    assert context.process.call_count == 2
    assert context.process.call_args_list[0].args == ('hello',)
    assert context.process.call_args_list[1].args == ('world',)

def test_throws_if_bad_header_format():
    with pytest.raises(formats.FormatError):
        formats.parse_diff(['hello'])
