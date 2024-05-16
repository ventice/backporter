from unittest.mock import Mock, MagicMock
import pytest

@pytest.fixture
def mock_system(monkeypatch):
    system = Mock()
    system.read_lines.return_value = []
    system.diff.return_value.returncode = 1
    system.patch.return_value.returncode = 0
    monkeypatch.setattr('backport.System', system)
    return system

@pytest.fixture
def mock_tempdir(monkeypatch):
    temp = MagicMock()
    temp.return_value.__enter__.return_value = 'testdir'
    monkeypatch.setattr('tempfile.TemporaryDirectory', temp)
    return temp

