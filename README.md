# coder2api

A unified wrapper for [Gemini CLI Proxy](https://github.com/bitnom/gemini-cli-proxy), [Claude Code API](https://github.com/codingworkflow/claude-code-api), and [ChatMock](https://github.com/RayBytes/ChatMock).

This tool provides a single entry point to run and manage these local coding agent proxies, exposing them via a unified API endpoint.

## Prerequisites

- **Python 3.13+**
- **Node.js & npm** (Required for Gemini CLI Proxy)

## Quick Start

You can run `coder2api` directly without installing it using `uvx` (part of [uv](https://github.com/astral-sh/uv)):

```bash
uvx coder2api serve
```

Or using `pipx`:

```bash
pipx run coder2api serve
```

This command will:
1.  Download the package.
2.  Automatically install Node.js dependencies for the Gemini proxy (if missing).
3.  Start all services and the unified proxy.

## Installation

If you prefer to install it globally:

### Using pipx (Recommended)

```bash
pipx install coder2api
coder2api serve
```

### Using uv

```bash
uv tool install coder2api
coder2api serve
```

## Usage

### Unified Server

The primary command starts all backend services and the proxy:

```bash
coder2api serve
```

This starts:
- **Gemini CLI Proxy** on port `3001`
- **ChatMock** on port `3002`
- **Claude Code API** on port `3003`
- **Unified Proxy** on port `8069`

You can access the APIs via the proxy:
- **Codex (ChatMock)**: `http://localhost:8069/codex/v1/...`
- **Claude Code**: `http://localhost:8069/cc/v1/...`
- **Gemini**: `http://localhost:8069/gemini/openai/...` or `http://localhost:8069/gemini/anthropic/...`

### CLI Wrappers

You can also use the CLI wrappers for individual tools:

**ChatMock (Codex):**
```bash
coder2api codex --help
coder2api codex login
```

**Claude Code API:**
```bash
coder2api cc
```

**Gemini CLI Proxy:**
```bash
coder2api gemini -- --help
```

## Development

If you want to contribute or run from source:

1.  Clone the repository.
2.  Install dependencies using `uv`:

```bash
uv sync
```

3.  Run using `uv run`:

```bash
uv run coder2api serve
```

## Logs

Logs for the background services are written to the `logs/` directory in the working directory where you run the command.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.