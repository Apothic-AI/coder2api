# coder2api

A unified wrapper for [Gemini CLI Proxy](coders/gemini-cli-proxy), [Claude Code API](coders/claude-code-api), and [ChatMock](coders/ChatMock).

This tool provides a single entry point to run and manage these local coding agent proxies, exposing them via a unified API endpoint.

## Installation

This project uses `uv` for dependency management.

```bash
uv sync
```

Ensure you have built the Node.js dependency for Gemini Proxy:

```bash
cd coders/gemini-cli-proxy
npm install && npm run build
cd ../..
```

## Usage

### Unified Server

Start all services and the unified proxy:

```bash
uv run main.py serve
```

This will start:
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
uv run main.py codex --help
uv run main.py codex login
```

**Claude Code API:**
```bash
uv run main.py cc
```

**Gemini CLI Proxy:**
```bash
uv run main.py gemini -- --help
```

## Logs

Logs for the background services are written to the `logs/` directory when running `serve`.