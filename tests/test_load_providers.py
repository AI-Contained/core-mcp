import importlib.metadata
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that  # type: ignore[import-untyped]
from fastmcp import FastMCP

from ai_contained.core.mcp import load_providers


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


def describe_load_providers():

    @pytest.fixture
    def mcp():
        return FastMCP("test")

    @pytest.fixture
    def provider(monkeypatch):
        # Clear any env vars that may be set in the host environment so tests
        # start from a known baseline and only see what they explicitly configure.
        monkeypatch.delenv("ALLOWED_PROVIDERS", raising=False)
        monkeypatch.delenv("DENIED_PROVIDERS", raising=False)
        return MockProvider(monkeypatch)

    def describe_with_no_env_vars():
        def it_loads_all_discovered_providers(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            provider.set_tools(fs, shell)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(1)

        def it_returns_the_mcp_instance(mcp, provider):
            provider.set_tools()

            result = load_providers(mcp)

            assert_that(result).is_same_as(mcp)

    def describe_ALLOWED_PROVIDERS():
        def it_loads_only_the_allowed_provider(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            provider.set_tools(fs, shell)
            provider.setenv("ALLOWED_PROVIDERS", fs.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

        def it_loads_multiple_allowed_providers(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            git = MockTool("git")
            provider.set_tools(fs, shell, git)
            provider.setenv("ALLOWED_PROVIDERS", f"{fs.name},{shell.name}")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(1)
            assert_that(git.times_called()).is_equal_to(0)

        def it_loads_nothing_when_no_providers_match(mcp, provider):
            fs = MockTool("filesystem")
            provider.set_tools(fs)
            provider.setenv("ALLOWED_PROVIDERS", "shell")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_is_case_sensitive(mcp, provider):
            fs = MockTool("filesystem")
            provider.set_tools(fs)
            provider.setenv("ALLOWED_PROVIDERS", "Filesystem")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_does_not_load_when_name_has_surrounding_whitespace(mcp, provider):
            fs = MockTool("filesystem")
            provider.set_tools(fs)
            provider.setenv("ALLOWED_PROVIDERS", f" {fs.name} ")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_treats_comma_only_value_as_unset(mcp, provider):
            fs = MockTool("filesystem")
            provider.set_tools(fs)
            provider.setenv("ALLOWED_PROVIDERS", ",")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)

    def describe_DENIED_PROVIDERS():
        def it_skips_the_denied_provider(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            provider.set_tools(fs, shell)
            provider.setenv("DENIED_PROVIDERS", shell.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

        def it_skips_multiple_denied_providers(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            git = MockTool("git")
            provider.set_tools(fs, shell, git)
            provider.setenv("DENIED_PROVIDERS", f"{shell.name},{git.name}")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)
            assert_that(git.times_called()).is_equal_to(0)

        def it_loads_all_when_no_providers_match_deny_list(mcp, provider):
            fs = MockTool("filesystem")
            provider.set_tools(fs)
            provider.setenv("DENIED_PROVIDERS", "shell")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)

    def describe_ALLOWED_and_DENIED_together():
        def it_applies_deny_after_allow(mcp, provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            provider.set_tools(fs, shell)
            provider.setenv("ALLOWED_PROVIDERS", f"{fs.name},{shell.name}")
            provider.setenv("DENIED_PROVIDERS", shell.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

    def describe_error_handling():
        def it_raises_and_halts_when_register_fails(mcp, provider):
            def fail(mcp):
                raise RuntimeError("register failed")

            bad = MockTool("bad")
            bad._ep.load.return_value = fail
            good = MockTool("good")
            provider.set_tools(bad, good)

            with pytest.raises(RuntimeError, match="register failed"):
                load_providers(mcp)

            assert_that(good.times_called()).is_equal_to(0)
