import json

import pytest
from assertpy import assert_that
from fastmcp.client.client import CallToolResult
from mcp.types import TextContent

from ai_contained.core.mcp.testing import Elicitor, WrapCallToolResult


def make_result(text: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=None,
        meta=None,
    )


def describe_elicitor():

    @pytest.mark.parametrize("method", ["accept", "decline", "cancel"])
    async def it_returns_the_correct_action_and_none_content(method):
        e = Elicitor()
        getattr(e, method)()
        result = await e("msg", None, None, None)
        assert_that(result.action).is_equal_to(method)
        assert_that(result.content).is_none()

    @pytest.mark.parametrize("method", ["accept", "decline", "cancel"])
    async def it_raises_on_message_mismatch(method):
        e = Elicitor()
        getattr(e, method)(expect_message="expected")
        with pytest.raises(AssertionError) as exc_info:
            await e("actual", None, None, None)
        assert_that(str(exc_info.value)).contains("expected").contains("actual")

    def describe_accept():
        async def it_returns_provided_value():
            e = Elicitor()
            e.accept({"key": "value"})
            result = await e("msg", None, None, None)
            assert_that(result.content).is_equal_to({"key": "value"})

        async def it_passes_when_message_matches():
            e = Elicitor()
            e.accept(expect_message="expected")
            result = await e("expected", None, None, None)
            assert_that(result.action).is_equal_to("accept")

    def describe_queue_behaviour():
        async def it_raises_on_unexpected_elicitation():
            e = Elicitor()
            with pytest.raises(AssertionError) as exc_info:
                await e("surprise", None, None, None)
            assert_that(str(exc_info.value)).contains("surprise")

        async def it_consumes_steps_in_fifo_order():
            e = Elicitor()
            e.accept().decline().cancel()
            r1 = await e("msg", None, None, None)
            r2 = await e("msg", None, None, None)
            r3 = await e("msg", None, None, None)
            assert_that(r1.action).is_equal_to("accept")
            assert_that(r2.action).is_equal_to("decline")
            assert_that(r3.action).is_equal_to("cancel")

        async def it_raises_after_all_steps_consumed():
            e = Elicitor()
            e.accept()
            await e("msg", None, None, None)
            with pytest.raises(AssertionError):
                await e("msg", None, None, None)

    def describe_on_elicit():
        async def it_accepts_a_custom_callback():
            e = Elicitor()
            e.on_elicit(lambda msg, rtype, params, ctx: ("accept", "custom"))
            result = await e("msg", None, None, None)
            assert_that(result.action).is_equal_to("accept")
            assert_that(result.content).is_equal_to("custom")

        def it_returns_self_for_chaining():
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
