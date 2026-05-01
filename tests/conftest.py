import importlib.metadata
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP


@pytest.fixture
def mcp():
    return FastMCP("test")


class MockTool:
    def __init__(self, name):
        self.name = name
        self._calls = []

        def register(mcp):
            self._calls.append(mcp)

        ep = MagicMock()
        ep.name = name
        ep.load.return_value = register
        self._ep = ep

    def times_called(self):
        return len(self._calls)


class MockProvider:
    def __init__(self, monkeypatch):
        self._mp = monkeypatch

    def set_tools(self, *tools):
        self._mp.setattr(
            importlib.metadata,
            "entry_points",
            lambda group=None: [t._ep for t in tools],
        )

    def setenv(self, key, value):
        self._mp.setenv(key, value)


@pytest.fixture
def mock_provider(monkeypatch):
    return MockProvider(monkeypatch)
