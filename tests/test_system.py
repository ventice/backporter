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
    monkeypatch.setattr('backport.SystemMerger', sysmerger)
    import backport
    backport.merge('before', 'after', 'target')
    assert sysmerger.call_args.args == ('before', 'after', 'testdir')

def test_temp_directory_is_used_for_patch(monkeypatch):
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=0)))
    patch = Mock()
    monkeypatch.setattr('backport.SystemPatch', patch)
    import backport
    backport.SystemMerger('before', 'after', 'testdir').get_diff()
    assert patch.call_args.args == ('testdir/diff.patch', 'testdir')

def test_patch_is_applied_to_target(monkeypatch):
    patch = Mock()
    monkeypatch.setattr('backport.SystemMerger', Mock(return_value=Mock(get_diff=Mock(return_value=patch))))
    import backport
    backport.merge('before', 'after', 'target')
    assert patch.apply.call_args.args == ('target',)


def test_system_is_used_for_diff(monkeypatch):
    system = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr('subprocess.run', system)
    import backport
    backport.SystemMerger('before.c', 'after.c', 'tempdir').get_diff()
    assert system.call_args.args == ('diff after.c before.c > tempdir/diff.patch',)

def test_diff_does_not_throw_when_diffs_are_found(monkeypatch):
    # diff returns 1 when diffs are found
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=1))) 
    import backport
    backport.SystemMerger('before.c', 'after.c', 'tempdir').get_diff()


def test_diff_throws_on_trouble(monkeypatch):
    # 2 in case of any trouble
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=2)))
    import backport
    with pytest.raises(RuntimeError):
        backport.SystemMerger('before.c', 'after.c', 'tempdir').get_diff()


def test_system_is_used_for_patch(monkeypatch):
    system = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr('subprocess.run', system)
    import backport
    backport.SystemPatch('test.patch', 'tempdir').apply('target')
    assert system.call_args.args == ('patch -r tempdir/reject target test.patch',)

def test_returns_no_rejection_on_successful_patch(monkeypatch):
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=0)))
    import backport
    rejection = backport.SystemPatch('_', '_').apply('target')
    assert rejection is None

def test_returns_rejection_on_conflict(monkeypatch):
    # Exit code of patch when conflict
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=1)))
    import backport
    rejection = backport.SystemPatch('_', '_').apply('target')
    assert rejection is not None


def test_throws_if_patching_fails_for_other_reason(monkeypatch):
    # Exit code different from merge conflict
    monkeypatch.setattr('subprocess.run', Mock(return_value=Mock(returncode=2)))
    import backport
    with pytest.raises(RuntimeError):
        backport.SystemPatch('_', '_').apply('target')

