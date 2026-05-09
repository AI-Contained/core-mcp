# ai-contained-base

The base Docker image and Python library for [AI-Contained](https://github.com/AI-Contained) MCP servers.

This repo contains two packages:

| Package | Description |
|---|---|
| `ai-contained-core-mcp` | Provider auto-discovery via Python entry points |
| `ai-contained-base` | MCP HTTP server + provider finalization scripts |

## Docker image

```bash
docker pull ghcr.io/ai-contained/ai-contained-base:latest
```

The image exposes an MCP server over HTTP. Providers are installed by assembling a final image on top of the base:

```dockerfile
FROM ghcr.io/ai-contained/ai-contained-base:latest

COPY --link --from=ghcr.io/ai-contained/ai-contained-provider-shell:latest / /

RUN ai-contained-finalize

USER 65533:65533
```

`ai-contained-finalize` installs all provider packages found under `/opt/ai-contained-*/` into the system Python.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ADDRESS` | `0.0.0.0` | Address the MCP server binds to |
| `PORT` | `8080` | Port the MCP server listens on |
| `ALLOWED_PROVIDERS` | _(all)_ | Comma-separated list of provider names to load |
| `DENIED_PROVIDERS` | _(none)_ | Comma-separated list of provider names to skip |

`ALLOWED_PROVIDERS` and `DENIED_PROVIDERS` are case-sensitive and match the entry point name exactly. `DENIED_PROVIDERS` takes precedence.

## Packages

### `ai-contained-core-mcp`

Provides `load_providers` — auto-discovers all packages registered under the `ai_contained.provider` entry point group:

```python
from fastmcp import FastMCP
from ai_contained.core.mcp import load_providers

mcp = FastMCP("my-server")
load_providers(mcp)
```

Also provides `ai_contained.core.mcp.testing` with test utilities (`Elicitor`, `WrapCallToolResult`) for use in provider test suites.

### `ai-contained-base`

Provides two console scripts:

- **`ai-contained-server`** — starts the MCP HTTP server
- **`ai-contained-finalize`** — installs providers at image build time

## Creating a Provider

1. Create a package with a `register(mcp: FastMCP) -> None` function
2. Declare the entry point in `pyproject.toml`:

```toml
[project.entry-points."ai_contained.provider"]
myprovider = "my_package:register"
```

3. Ship it as a Docker image following the provider convention — `ai-contained-finalize` will discover and install it automatically.

See [ai-contained-provider-template](https://github.com/AI-Contained/ai-contained-provider-template) for a reference implementation.
