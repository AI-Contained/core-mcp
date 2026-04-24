# core-mcp

The base plugin loader for [AI-Contained](https://github.com/AI-Contained) MCP servers. Provides auto-discovery of installed plugins via Python entry points.

## Usage

```python
from fastmcp import FastMCP
from ai_contained.core.mcp import load_plugins

mcp = FastMCP("my-server")
load_plugins(mcp)
```

`load_plugins` discovers all packages registered under the `ai_contained.plugins` entry point group and loads them into the provided `FastMCP` instance.

## Installation

```bash
pip install "ai-contained-core-mcp @ https://github.com/AI-Contained/core-mcp/archive/refs/tags/v0.0.1.zip"
```

## Creating a Plugin

1. Create a package with a `register(mcp)` function
2. Register it in `pyproject.toml`:

```toml
[project.entry-points."ai_contained.plugins"]
myplugin = "my_package:register"
```

3. Install it - `load_plugins` will discover it automatically.

See [ai-contained-provider-template](https://github.com/AI-Contained/ai-contained-provider-template) for a reference implementation.
