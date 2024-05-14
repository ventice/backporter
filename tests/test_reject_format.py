import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from unittest.mock import Mock
import formats

def test_parse_reject_file():
    lines = [
        '*** /dev/null',
        '--- /dev/null',
        '***************',
        '*** 3,4',
        '- hello',
        '- world',
        '--- 3,4 -----',
        '+ salve',
        '+ munde',
        '***************',
        '*** 6',
        '- bye',
        '--- 0 -----',
    ]
    hunks = formats.parse_reject(lines)
    assert len(hunks) == 2
    assert hunks[0].type == formats.ChangeType.CHANGED
    assert hunks[0].source.begin == 3
    assert hunks[0].source.end == 4
    assert hunks[0].source.body == ['hello', 'world']
    assert hunks[0].destination.begin == 3
    assert hunks[0].destination.end == 4
    assert hunks[0].destination.body == ['salve', 'munde']

    assert hunks[1].type == formats.ChangeType.CHANGED
    assert hunks[1].source.begin == 6
    assert hunks[1].source.end == 6
    assert hunks[1].source.body == ['bye']
    assert hunks[1].destination.begin == 0
    assert hunks[1].destination.end == 0
    assert hunks[1].destination.body is None

def test_parse_reject_raises_on_garbage():
    with pytest.raises(formats.FormatError):
        formats.parse_reject(['skip', 'skip', 'bad', 'format'])