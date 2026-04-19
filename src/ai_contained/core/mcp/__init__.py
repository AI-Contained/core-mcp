"""AI-Contained plugin loader for FastMCP."""
import importlib.metadata
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger

logger = get_logger("ai_contained")


def load_plugins(mcp: FastMCP) -> FastMCP:
    """Auto-discover and load all installed ai_contained plugins into a FastMCP instance."""
    for entry_point in importlib.metadata.entry_points(group="ai_contained.plugins"):
        try:
            plugin = entry_point.load()
            plugin(mcp)
            logger.info(f"✅ Loaded AI-Contained plugin: {entry_point.name}")
        except Exception as e:
            logger.error(f"❌ Failed to load AI-Contained plugin '{entry_point.name}': {e}")
    return mcp
