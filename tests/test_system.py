from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from formats import Hunk, Chunk, ChangeType
import backport

def test_temp_directory_is_used_for_diff_and_patch(mock_tempdir, mock_system):
    mock_tempdir.return_value.__enter__.return_value = 'testdir'
    backport.merge('before', 'after', 'target')
    assert mock_system.diff.call_args.args[2] == 'testdir/diff.patch'
    assert mock_system.patch.call_args.args[1] == 'testdir/diff.patch'
    assert mock_system.patch.call_args.args[2] == 'testdir/reject'

def test_patch_is_applied_to_target(mock_system, mock_tempdir):
    mock_system.diff.return_value = Mock(returncode=1)
    mock_system.patch.return_value = Mock(returncode=0)
    backport.merge('before', 'after', 'target')
    assert mock_system.patch.call_args.args[0] == 'target'

def test_diff_throws_on_trouble(mock_system):
    # 2 in case of any trouble
    mock_system.diff.return_value.returncode = 2
    mock_system.patch.return_value.returncode = 0
    with pytest.raises(RuntimeError):
        backport.merge('before.c', 'after.c', 'tempdir')

def test_system_is_used_for_patch(mock_system, mock_tempdir):
    mock_tempdir.return_value.__enter__.return_value = 'tempdir'
    mock_system.patch.return_value.returncode = 0
    backport.merge('before', 'after', 'target')
    assert mock_system.patch.call_args.args == ('target', 'tempdir/diff.patch', 'tempdir/reject',)


def test_throws_if_patching_fails_for_other_reason(mock_system):
    # Exit code different from merge conflict
    mock_system.patch.return_value.returncode = 2 
    with pytest.raises(RuntimeError):
        backport.merge('before', 'after', 'target')

def test_system_redirects_diff_output_to_patch_file(monkeypatch):
    run = Mock()
    monkeypatch.setattr('subprocess.run', run)
    backport.System.diff('before', 'after', 'patch')
    assert run.call_args.args == ('diff before after > patch',)

def test_system_invokes_patch(monkeypatch):
    run = Mock()
    monkeypatch.setattr('subprocess.run', run)
    backport.System.patch('target', 'patch', 'reject')
    assert run.call_args.args == ('patch -f -r reject target patch',)

def test_patch_parses_diff_file_contents(mock_system, monkeypatch):
    mock_system.read_lines.side_effect = [
        ['diff line 1', 'diff line 2'],
        ['skip', 'skip'],
    ]
    parse_diff = Mock()
    parsed_hunks = [Hunk(ChangeType.ADDED, Chunk(begin=1), None)]
    parse_diff.return_value = parsed_hunks
    monkeypatch.setattr('formats.parse_diff', parse_diff)
    hunks = backport.merge('before', 'after', 'target')
    assert parse_diff.call_args.args[0] == ['diff line 1', 'diff line 2']
    assert list(hunks.values()) == parsed_hunks

def test_reject_parses_the_reject_file(mock_system, mock_tempdir, monkeypatch):
    mock_tempdir.return_value.__enter__.return_value = 'testdir'
    mock_system.patch.return_value.returncode = 1 # There are conflicts
    mock_system.read_lines = lambda fn: {
            'testdir/diff.patch': [],
            'target': ['target line 1', 'target line 2'],
            'testdir/reject': ['reject line 1', 'reject line 2']
    }.get(fn, [])
    parse_reject = Mock()
    parsed_hunks = [Hunk(ChangeType.CHANGED, Chunk(2, 3, []), Chunk(2, 3, []))]
    parse_reject.return_value = parsed_hunks
    monkeypatch.setattr('formats.parse_reject', parse_reject)
    hunks = backport.merge('before', 'after', 'target')
    assert parse_reject.call_args.args[0] == ['reject line 1', 'reject line 2']
    assert list(hunks.values()) == parsed_hunks

def test_finds_conflicts():
    hunk = Hunk(
        ChangeType.CHANGED,
        Chunk(1, 2, ['Hello', 'World']),
        Chunk(1, 2, ['Hello', 'World!'])
    )
    assert backport.get_conflicts(hunk) == {2: ('World', 'World!')}