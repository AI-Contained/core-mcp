"""MCP server entry point."""

import argparse
import os

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from ai_contained.core.mcp import load_providers

mcp = FastMCP("ai-contained")
load_providers(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):  # type: ignore[no-untyped-def]
    """Return server health status."""
    return JSONResponse({"status": "healthy"})


def main() -> None:
    """Start the MCP HTTP server."""
    parser = argparse.ArgumentParser(description="AI-Contained MCP server")
    parser.add_argument("--host", default=os.getenv("ADDRESS", "0.0.0.0"), help="Address to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")), help="Port to listen on")
    args = parser.parse_args()

    mcp.run(
        transport="http",
        host=args.host,
        port=args.port,
        show_banner=False,
    )


if __name__ == "__main__":
    main()
