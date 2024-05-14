import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_system(monkeypatch):
    system = Mock()
    monkeypatch.setattr('backport.System', system)
    return system

