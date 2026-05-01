import pytest
from assertpy import assert_that  # type: ignore[import-untyped]

from ai_contained.core.mcp import load_providers
from conftest import MockTool  # type: ignore[import-not-found]


def describe_load_providers():

    def describe_with_no_env_vars():
        def it_loads_all_discovered_providers(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            mock_provider.set_tools(fs, shell)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(1)

        def it_returns_the_mcp_instance(mcp, mock_provider):
            mock_provider.set_tools()

            result = load_providers(mcp)

            assert_that(result).is_same_as(mcp)

    def describe_ALLOWED_PROVIDERS():
        def it_loads_only_the_allowed_provider(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            mock_provider.set_tools(fs, shell)
            mock_provider.setenv("ALLOWED_PROVIDERS", fs.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

        def it_loads_multiple_allowed_providers(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            git = MockTool("git")
            mock_provider.set_tools(fs, shell, git)
            mock_provider.setenv("ALLOWED_PROVIDERS", f"{fs.name},{shell.name}")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(1)
            assert_that(git.times_called()).is_equal_to(0)

        def it_loads_nothing_when_no_providers_match(mcp, mock_provider):
            fs = MockTool("filesystem")
            mock_provider.set_tools(fs)
            mock_provider.setenv("ALLOWED_PROVIDERS", "shell")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_is_case_sensitive(mcp, mock_provider):
            fs = MockTool("filesystem")
            mock_provider.set_tools(fs)
            mock_provider.setenv("ALLOWED_PROVIDERS", "Filesystem")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_does_not_load_when_name_has_surrounding_whitespace(mcp, mock_provider):
            fs = MockTool("filesystem")
            mock_provider.set_tools(fs)
            mock_provider.setenv("ALLOWED_PROVIDERS", f" {fs.name} ")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(0)

        def it_treats_comma_only_value_as_unset(mcp, mock_provider):
            fs = MockTool("filesystem")
            mock_provider.set_tools(fs)
            mock_provider.setenv("ALLOWED_PROVIDERS", ",")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)

    def describe_DENIED_PROVIDERS():
        def it_skips_the_denied_provider(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            mock_provider.set_tools(fs, shell)
            mock_provider.setenv("DENIED_PROVIDERS", shell.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

        def it_skips_multiple_denied_providers(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            git = MockTool("git")
            mock_provider.set_tools(fs, shell, git)
            mock_provider.setenv("DENIED_PROVIDERS", f"{shell.name},{git.name}")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)
            assert_that(git.times_called()).is_equal_to(0)

        def it_loads_all_when_no_providers_match_deny_list(mcp, mock_provider):
            fs = MockTool("filesystem")
            mock_provider.set_tools(fs)
            mock_provider.setenv("DENIED_PROVIDERS", "shell")

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)

    def describe_ALLOWED_and_DENIED_together():
        def it_applies_deny_after_allow(mcp, mock_provider):
            fs = MockTool("filesystem")
            shell = MockTool("shell")
            mock_provider.set_tools(fs, shell)
            mock_provider.setenv("ALLOWED_PROVIDERS", f"{fs.name},{shell.name}")
            mock_provider.setenv("DENIED_PROVIDERS", shell.name)

            load_providers(mcp)

            assert_that(fs.times_called()).is_equal_to(1)
            assert_that(shell.times_called()).is_equal_to(0)

    def describe_error_handling():
        def it_raises_and_halts_when_register_fails(mcp, mock_provider):
            def fail(mcp):
                raise RuntimeError("register failed")

            bad = MockTool("bad")
            bad._ep.load.return_value = fail
            good = MockTool("good")
            mock_provider.set_tools(bad, good)

            with pytest.raises(RuntimeError, match="register failed"):
                load_providers(mcp)

            assert_that(good.times_called()).is_equal_to(0)
