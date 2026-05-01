import importlib.metadata
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that  # type: ignore[import-untyped]
from fastmcp import FastMCP

from ai_contained.core.mcp import load_providers


class MockProvider:
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


class MockContext:
    def __init__(self, monkeypatch):
        self._mp = monkeypatch

    def set_providers(self, *providers):
        self._mp.setattr(
            importlib.metadata,
            "entry_points",
            lambda group=None: [p._ep for p in providers],
        )

    def setenv(self, key, value):
        self._mp.setenv(key, value)


def describe_load_providers():

    @pytest.fixture
    def mcp():
        return FastMCP("test")

    @pytest.fixture
    def context(monkeypatch):
        # Clear any env vars that may be set in the host environment so tests
        # start from a known baseline and only see what they explicitly configure.
        monkeypatch.delenv("ALLOWED_PROVIDERS", raising=False)
        monkeypatch.delenv("DENIED_PROVIDERS", raising=False)
        return MockContext(monkeypatch)

    @pytest.fixture
    def providers(context):
        fs = MockProvider("filesystem")
        shell = MockProvider("shell")
        git = MockProvider("git")
        context.set_providers(fs, shell, git)
        return SimpleNamespace(filesystem=fs, shell=shell, git=git)

    def describe_with_no_env_vars():
        def it_loads_all_discovered_providers(mcp, providers):
            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

        def it_returns_the_mcp_instance(mcp, providers):
            result = load_providers(mcp)

            assert_that(result).is_same_as(mcp)
            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_ALLOWED_PROVIDERS():
        def it_loads_only_the_allowed_provider(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", providers.filesystem.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_multiple_allowed_providers(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", f"{providers.filesystem.name},{providers.shell.name}")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_nothing_when_no_providers_match(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", "non-existent")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_is_case_sensitive(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", "Filesystem")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_does_not_load_when_name_has_surrounding_whitespace(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", f" {providers.filesystem.name} ")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_treats_comma_only_value_as_unset(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", ",")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_DENIED_PROVIDERS():
        def it_skips_the_denied_provider(mcp, context, providers):
            context.setenv("DENIED_PROVIDERS", providers.shell.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(1)

        def it_skips_multiple_denied_providers(mcp, context, providers):
            context.setenv("DENIED_PROVIDERS", f"{providers.shell.name},{providers.git.name}")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_all_when_no_providers_match_deny_list(mcp, context, providers):
            context.setenv("DENIED_PROVIDERS", "non-existent")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_ALLOWED_and_DENIED_together():
        def it_applies_deny_after_allow(mcp, context, providers):
            context.setenv("ALLOWED_PROVIDERS", f"{providers.filesystem.name},{providers.shell.name}")
            context.setenv("DENIED_PROVIDERS", providers.shell.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

    def describe_error_handling():
        def it_raises_and_halts_when_register_fails(mcp, context):
            def fail(mcp):
                raise RuntimeError("register failed")

            bad = MockProvider("bad")
            bad._ep.load.return_value = fail
            good = MockProvider("good")
            context.set_providers(bad, good)

            with pytest.raises(RuntimeError, match="register failed"):
                load_providers(mcp)

            assert_that(good.times_called()).is_equal_to(0)
