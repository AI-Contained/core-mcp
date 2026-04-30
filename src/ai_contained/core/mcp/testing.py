import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Self

from fastmcp.client.client import CallToolResult
from fastmcp.client.elicitation import ElicitRequestParams, ElicitResult
from mcp.client.session import ClientSession
from mcp.types import TextContent
from mcp.shared.context import RequestContext

ElicitAction = Literal["accept", "decline", "cancel"]
ElicitContent = dict[str, Any] | str | int | float | bool | None
ElicitResponse = tuple[ElicitAction, ElicitContent]
ElicitCallback = Callable[
    [str, type | None, ElicitRequestParams, RequestContext[ClientSession, Any]],
    ElicitResponse,
]


class Elicitor:
    """Queue-based elicitation handler for use in tests.

    Each test step registers an expected elicitation response using accept(),
    decline(), or cancel(). When the MCP server triggers an elicitation, the
    next queued step is consumed and its response returned. Unconsumed steps
    at the end of a test indicate a bug — use the elicitor fixture to assert
    the queue is empty after each test.

    Typical usage via the elicitor fixture in conftest.py:

        def it_does_something(execute_bash, elicitor):
            elicitor.accept(expect_message="run: echo hi")
            result = await execute_bash("echo hi")
    """

    def __init__(self) -> None:
        self._queue: list[ElicitCallback] = []

    def _make_step(self, action: ElicitAction, content: ElicitContent, expect_message: str | None) -> ElicitCallback:
        """Build a single elicitation callback that returns the given action and content.

        Args:
            action: The elicitation response action ("accept", "decline", or "cancel").
            content: The value to return alongside the action. None for decline/cancel.
            expect_message: If provided, the callback asserts the incoming message matches
                exactly before responding. Raises AssertionError on mismatch.

        Returns:
            An ElicitCallback suitable for passing to on_elicit().
        """
        def step(msg: str, rtype: type | None, params: ElicitRequestParams, ctx: RequestContext[ClientSession, Any]) -> ElicitResponse:
            if expect_message is not None and msg != expect_message:
                assert msg == expect_message, f"elicitation message mismatch\n  expected: {expect_message!r}\n  got:      {msg!r}"
            return (action, content)
        return step

    def on_elicit(self, fn: ElicitCallback) -> Self:
        """Enqueue a raw elicitation callback.

        Args:
            fn: A callable matching ElicitCallback that receives the elicitation
                message, response type, params, and context, and returns an
                (action, content) tuple.

        Returns:
            Self, to allow fluent chaining.
        """
        self._queue.append(fn)
        return self

    def accept(self, value: ElicitContent = None, *, expect_message: str | None = None) -> Self:
        """Enqueue a step that responds with "accept".

        Args:
            value: The content to return with the accept response. Defaults to None.
            expect_message: If provided, asserts the elicitation message equals this
                string exactly. Raises AssertionError on mismatch.

        Returns:
            Self, to allow fluent chaining.
        """
        return self.on_elicit(self._make_step("accept", value, expect_message))

    def decline(self, *, expect_message: str | None = None) -> Self:
        """Enqueue a step that responds with "decline".

        Args:
            expect_message: If provided, asserts the elicitation message equals this
                string exactly. Raises AssertionError on mismatch.

        Returns:
            Self, to allow fluent chaining.
        """
        return self.on_elicit(self._make_step("decline", None, expect_message))

    def cancel(self, *, expect_message: str | None = None) -> Self:
        """Enqueue a step that responds with "cancel".

        Args:
            expect_message: If provided, asserts the elicitation message equals this
                string exactly. Raises AssertionError on mismatch.

        Returns:
            Self, to allow fluent chaining.
        """
        return self.on_elicit(self._make_step("cancel", None, expect_message))

    async def __call__(self, message: str, response_type: type | None, params: ElicitRequestParams, context: RequestContext[ClientSession, Any]) -> ElicitResult:
        """Handle an incoming elicitation from the MCP server.

        Consumes the next queued step and returns its response. Raises AssertionError
        if the queue is empty, which indicates the test received more elicitations
        than it registered steps for.

        Args:
            message: The elicitation prompt sent by the server.
            response_type: The expected response schema type, if any.
            params: Raw elicitation request parameters from the MCP protocol.
            context: The MCP request context for the current session.

        Returns:
            An ElicitResult containing the action and content from the next queued step.

        Raises:
            AssertionError: If no steps are queued (unexpected elicitation).
            AssertionError: If the queued step has an expect_message that does not match.
        """
        action, content = self._queue.pop(0)(message, response_type, params, context)
        return ElicitResult(action=action, content=content)


@dataclass
class WrapCallToolResult(CallToolResult):
    """Extends CallToolResult with a convenience method for JSON tool responses.

    MCP tools that return a JSON string as their sole content block can be
    deserialized directly via .json() rather than manually parsing content[0].text.
    """

    def json(self) -> Any:
        """Deserialize the first content block as JSON.

        Returns:
            The parsed Python object from content[0].text.

        Raises:
            json.JSONDecodeError: If the content is not valid JSON.
            IndexError: If the content list is empty.
        """
        text_content = self.content[0]
        assert isinstance(text_content, TextContent)
        return json.loads(text_content.text)
