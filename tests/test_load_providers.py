import importlib.metadata
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from assertpy import assert_that  # type: ignore[import-untyped]
from fastmcp import FastMCP

from ai_contained.core.mcp import load_providers


class MockProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self._calls: list[FastMCP] = []

        def register(mcp: FastMCP) -> None:
            self._calls.append(mcp)

        entry_point = MagicMock()
        entry_point.name = name
        entry_point.load.return_value = register
        self._entry_point: MagicMock = entry_point

    def times_called(self) -> int:
        return len(self._calls)


class MockContext:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mp = monkeypatch

    def set_providers(self, *providers: MockProvider) -> None:
        def fake_entry_points(group: str | None = None) -> list[MagicMock]:
            return [provider._entry_point for provider in providers]

        self._mp.setattr(importlib.metadata, "entry_points", fake_entry_points)

    def setenv(self, key: str, value: str) -> None:
        self._mp.setenv(key, value)


@dataclass
class ProviderSet:
    filesystem: MockProvider
    shell: MockProvider
    git: MockProvider


def describe_load_providers() -> None:

    @pytest.fixture
    def mcp() -> FastMCP:
        return FastMCP("test")

    @pytest.fixture
    def context(monkeypatch: pytest.MonkeyPatch) -> MockContext:
        # Clear any env vars that may be set in the host environment so tests
        # start from a known baseline and only see what they explicitly configure.
        monkeypatch.delenv("ALLOWED_PROVIDERS", raising=False)
        monkeypatch.delenv("DENIED_PROVIDERS", raising=False)
        return MockContext(monkeypatch)

    @pytest.fixture
    def providers(context: MockContext) -> ProviderSet:
        fs = MockProvider("filesystem")
        shell = MockProvider("shell")
        git = MockProvider("git")
        context.set_providers(fs, shell, git)
        return ProviderSet(filesystem=fs, shell=shell, git=git)

    def describe_with_no_env_vars() -> None:
        def it_loads_all_discovered_providers(mcp: FastMCP, providers: ProviderSet) -> None:
            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

        def it_returns_the_mcp_instance(mcp: FastMCP, providers: ProviderSet) -> None:
            result = load_providers(mcp)

            assert_that(result).is_same_as(mcp)
            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_ALLOWED_PROVIDERS() -> None:
        def it_loads_only_the_allowed_provider(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", providers.filesystem.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_multiple_allowed_providers(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", f"{providers.filesystem.name},{providers.shell.name}")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_nothing_when_no_providers_match(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", "non-existent")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_is_case_sensitive(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", "Filesystem")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_does_not_load_when_name_has_surrounding_whitespace(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", f" {providers.filesystem.name} ")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(0)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_treats_comma_only_value_as_unset(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", ",")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_DENIED_PROVIDERS() -> None:
        def it_skips_the_denied_provider(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("DENIED_PROVIDERS", providers.shell.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(1)

        def it_skips_multiple_denied_providers(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("DENIED_PROVIDERS", f"{providers.shell.name},{providers.git.name}")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

        def it_loads_all_when_no_providers_match_deny_list(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("DENIED_PROVIDERS", "non-existent")

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(1)
            assert_that(providers.git.times_called()).is_equal_to(1)

    def describe_ALLOWED_and_DENIED_together() -> None:
        def it_applies_deny_after_allow(mcp: FastMCP, context: MockContext, providers: ProviderSet) -> None:
            context.setenv("ALLOWED_PROVIDERS", f"{providers.filesystem.name},{providers.shell.name}")
            context.setenv("DENIED_PROVIDERS", providers.shell.name)

            load_providers(mcp)

            assert_that(providers.filesystem.times_called()).is_equal_to(1)
            assert_that(providers.shell.times_called()).is_equal_to(0)
            assert_that(providers.git.times_called()).is_equal_to(0)

    def describe_error_handling() -> None:
        def it_raises_and_halts_when_register_fails(mcp: FastMCP, context: MockContext) -> None:
            def fail(mcp: FastMCP) -> None:
                raise RuntimeError("register failed")

            bad = MockProvider("bad")
            bad._entry_point.load.return_value = fail
            good = MockProvider("good")
            context.set_providers(bad, good)

            with pytest.raises(RuntimeError, match="register failed"):
                load_providers(mcp)

            assert_that(good.times_called()).is_equal_to(0)
