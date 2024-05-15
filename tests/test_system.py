import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
from unittest.mock import Mock, MagicMock


def test_temp_directory_is_used_for_diff(monkeypatch):
    temp = MagicMock()
    temp.return_value.__enter__.return_value = 'testdir'
    sysmerger = Mock()
    monkeypatch.setattr('tempfile.TemporaryDirectory', temp)
    monkeypatch.setattr('backport.Merger', sysmerger)
    import backport
    backport.merge('before', 'after', 'target')
    assert sysmerger.call_args.args == ('before', 'after', 'testdir')

def test_temp_directory_is_used_for_patch(monkeypatch, mock_system):
    mock_system.diff=Mock(return_value=Mock(returncode=0))
    patch = Mock()
    monkeypatch.setattr('backport.Patch', patch)
    import backport
    backport.Merger('before', 'after', 'testdir').get_diff()
    assert patch.call_args.args == ('testdir/diff.patch', 'testdir')

def test_patch_is_applied_to_target(monkeypatch):
    patch = Mock()
    monkeypatch.setattr('backport.Merger', Mock(return_value=Mock(get_diff=Mock(return_value=patch))))
    import backport
    backport.merge('before', 'after', 'target')
    assert patch.apply.call_args.args == ('target',)

def test_system_is_used_for_diff(mock_system):
    mock_system.diff=Mock(return_value=Mock(returncode=0))
    import backport
    backport.Merger('before.c', 'after.c', 'tempdir').get_diff()
    assert mock_system.diff.call_args.args == ('before.c', 'after.c',  'tempdir/diff.patch',)

def test_diff_does_not_throw_when_diffs_are_found(mock_system):
    # diff returns 1 when diffs are found
    mock_system.diff=Mock(return_value=Mock(returncode=1)) 
    import backport
    backport.Merger('before.c', 'after.c', 'tempdir').get_diff()


def test_diff_throws_on_trouble(mock_system):
    # 2 in case of any trouble
    mock_system.diff=Mock(return_value=Mock(returncode=2)) 
    import backport
    with pytest.raises(RuntimeError):
        backport.Merger('before.c', 'after.c', 'tempdir').get_diff()


def test_system_is_used_for_patch(mock_system):
    mock_system.patch=Mock(return_value=Mock(returncode=0))
    import backport
    backport.Patch('test.patch', 'tempdir').apply('target')
    assert mock_system.patch.call_args.args == ('target', 'test.patch', 'tempdir/reject',)

def test_returns_no_rejection_on_successful_patch(mock_system):
    mock_system.patch=Mock(return_value=Mock(returncode=0)) 
    import backport
    rejection = backport.Patch('_', '_').apply('target')
    assert rejection is None

def test_returns_rejection_on_conflict(mock_system):
    # Exit code of patch when conflict
    mock_system.patch=Mock(return_value=Mock(returncode=1)) 
    import backport
    rejection = backport.Patch('_', '_').apply('target')
    assert rejection is not None


def test_throws_if_patching_fails_for_other_reason(mock_system):
    # Exit code different from merge conflict
    mock_system.patch=Mock(return_value=Mock(returncode=2)) 
    import backport
    with pytest.raises(RuntimeError):
        backport.Patch('_', '_').apply('target')

def test_system_invokes_diff(monkeypatch):
    run = Mock()
    monkeypatch.setattr('subprocess.run', run)
    import backport
    backport.System.diff('before', 'after', 'patch')
    assert run.call_args.args == ('diff before after > patch',)


def test_system_invokes_patch(monkeypatch):
    run = Mock()
    monkeypatch.setattr('subprocess.run', run)
    import backport
    backport.System.patch('target', 'patch', 'reject')
    assert run.call_args.args == ('patch -f -r reject target patch',)

def test_patch_parses_diff_file_contents(mock_system, monkeypatch):
    mock_system.read = Mock(return_value=['hello', 'world'])
    parse_diff = Mock()
    import backport
    parsed_hunks = [backport.Hunk(None, None, None)]
    parse_diff.return_value = parsed_hunks
    monkeypatch.setattr('formats.parse_diff', parse_diff)
    hunks = backport.Patch('patch', 'tempdir').get_hunks()
    assert parse_diff.call_args.args[0] == ['hello', 'world']
    assert hunks == parsed_hunks

def test_reject_parses_the_reject_file(mock_system, monkeypatch):
    mock_system.read = Mock(return_value=['hello', 'world'])
    parse_reject = Mock()
    import backport
    parsed_hunks = [backport.Hunk(None, None, None)]
    parse_reject.return_value = parsed_hunks
    monkeypatch.setattr('formats.parse_reject', parse_reject)
    hunks = backport.Rejection('reject').get_hunks()
    assert parse_reject.call_args.args[0] == ['hello', 'world']
    assert hunks == parsed_hunks

def test_passes_hunks_to_processor(monkeypatch):
    reject = Mock()
    patch = Mock(apply=Mock(return_value=reject))
    monkeypatch.setattr('backport.Merger', Mock(return_value=Mock(get_diff=Mock(return_value=patch))))
    import backport
    processor = Mock()
    backport.merge('before', 'after', 'target', processor)
    assert processor.process_diff.call_args.args == (patch,)
    assert processor.process_reject.call_args.args == (reject,)
    assert processor.finalize.call_count == 1

def test_does_not_pass_hunks_if_no_rejection(monkeypatch):
    patch = Mock(apply=Mock(return_value=None))
    monkeypatch.setattr('backport.Merger', Mock(return_value=Mock(get_diff=Mock(return_value=patch))))
    import backport
    processor = Mock()
    backport.merge('before', 'after', 'target', processor)
    assert processor.process_reject.call_count == 0
