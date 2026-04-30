import json
from collections.abc import AsyncGenerator, Generator

import pytest
from assertpy import assert_that  # type: ignore[import-untyped]
from fastmcp import Context, FastMCP
from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from fastmcp.exceptions import ToolError
from mcp.types import TextContent

from ai_contained.core.mcp.testing import Elicitor, WrapCallToolResult


def make_result(text: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=None,
        meta=None,
    )


def describe_elicitor():

    @pytest.fixture
    def elicitor() -> Generator[Elicitor, None, None]:
        e = Elicitor()
        yield e
        assert_that(e._queue).is_empty()

    @pytest.fixture
    async def client(elicitor: Elicitor) -> AsyncGenerator[Client, None]:
        server = FastMCP("test")

        @server.tool()
        async def ask(message: str, ctx: Context) -> str:
            result = await ctx.elicit(message=message, response_type=None)
            if result.action != "accept":
                raise ToolError("cancelled")
            return "ok"

        async with Client(transport=server, elicitation_handler=elicitor) as c:
            yield c

    def describe_accept():
        async def it_succeeds(client, elicitor):
            elicitor.accept()
            result = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            assert_that(result.is_error).is_false()

        async def it_passes_when_message_matches(client, elicitor):
            expected = "hello"
            elicitor.accept(expect_message=expected)
            result = await client.call_tool("ask", {"message": expected}, raise_on_error=False)
            assert_that(result.is_error).is_false()

    @pytest.mark.parametrize("method", ["decline", "cancel"])
    async def it_returns_error_on_non_accept(client, elicitor, method):
        getattr(elicitor, method)()
        result = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
        assert_that(result.is_error).is_true()

    @pytest.mark.parametrize("method", ["accept", "decline", "cancel"])
    async def it_raises_on_message_mismatch(client, elicitor, method):
        expected_elicitation = "hello"
        received_elicitation = "goodbye"
        getattr(elicitor, method)(expect_message=expected_elicitation)
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("ask", {"message": received_elicitation})
        assert_that(str(exc_info.value)).contains(expected_elicitation).contains(received_elicitation)

    def describe_queue_behaviour():
        async def it_raises_when_queue_is_empty(client):
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool("ask", {"message": "hello"})
            assert_that(str(exc_info.value)).contains("pop from empty list")

        async def it_consumes_steps_in_fifo_order(client, elicitor):
            elicitor.accept().decline().accept()
            result1 = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            result2 = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            result3 = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            assert_that(result1.is_error).is_false()
            assert_that(result2.is_error).is_true()
            assert_that(result3.is_error).is_false()

        async def it_raises_when_queue_is_exhausted(client, elicitor):
            elicitor.accept()
            await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool("ask", {"message": "hello"})
            assert_that(str(exc_info.value)).contains("pop from empty list")

    def describe_on_elicit():
        async def it_accepts_a_custom_callback(client, elicitor):
            elicitor.on_elicit(lambda msg, rtype, params, ctx: ("accept", None))
            result = await client.call_tool("ask", {"message": "hello"}, raise_on_error=False)
            assert_that(result.is_error).is_false()

        def it_returns_self_for_chaining():
            # Inline — no MCP call, queue intentionally left with unconsumed step
            e = Elicitor()
            assert_that(e.on_elicit(lambda *_: ("accept", None))).is_same_as(e)


def describe_wrap_call_tool_result():

    def it_deserializes_json_content():
        wrapped = WrapCallToolResult(**vars(make_result('{"exit_status": "0"}')))
        assert_that(wrapped.json()).is_equal_to({"exit_status": "0"})

    def it_preserves_base_class_attributes():
        wrapped = WrapCallToolResult(**vars(make_result('{"k": "v"}')))
        assert_that(wrapped.is_error).is_false()
        assert_that(wrapped.content[0].text).is_equal_to('{"k": "v"}')

    def it_raises_on_invalid_json():
        wrapped = WrapCallToolResult(**vars(make_result("not json")))
        with pytest.raises(json.JSONDecodeError):
            wrapped.json()
