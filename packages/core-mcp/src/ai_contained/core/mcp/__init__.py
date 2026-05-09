"""AI-Contained provider loader for FastMCP."""

import importlib.metadata
import os

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger

logger = get_logger("ai_contained")


def _env_split_csv(env_var: str) -> list[str]:
    return [provider_name for provider_name in os.getenv(env_var, "").split(",") if provider_name]


def _is_allowed(provider_name: str, allowed: list[str], denied: list[str]) -> bool:
    if provider_name in denied:
        return False
    elif provider_name in allowed:
        return True
    elif len(allowed) == 0:  # no allow list means all providers are allowed
        return True
    return False


def load_providers(mcp: FastMCP) -> FastMCP:
    """Auto-discover and load all installed ai-contained providers into a FastMCP instance."""
    allowed = _env_split_csv("ALLOWED_PROVIDERS")
    denied = _env_split_csv("DENIED_PROVIDERS")
    for entry_point in importlib.metadata.entry_points(group="ai_contained.provider"):
        provider_name = entry_point.name
        version = f"v{entry_point.dist.version}" if entry_point.dist is not None else "v???"
        if not _is_allowed(provider_name, allowed, denied):
            logger.info(f"⏭️  Skipped AI-Contained provider: {provider_name} {version}")
            continue
        try:
            provider = entry_point.load()
            provider(mcp)
            logger.info(f"✅ Loaded AI-Contained provider: {provider_name} {version}")
        except Exception as e:
            logger.error(f"❌ Failed to load AI-Contained provider: {provider_name} {version} — {e}")
            raise
    return mcp
