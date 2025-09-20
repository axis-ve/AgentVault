# Repository Guidelines

## Project Structure & Responsibilities
The MCP package lives in `src/agentvault_mcp/`: `server.py` exposes the MCP server and CLI, `core.py` handles context trimming, `wallet.py` secures encrypted key stores, and `strategies.py` with `strategy_manager.py` orchestrate flows. Integrations sit in `adapters/` (OpenAI, Ollama, Web3). Top-level `docs/` captures integration notes, `examples/` holds orchestrations, and `scripts/` hosts automation. Root-level `test_*.py` suites mirror the module layout.

## Local Setup & Environment
Use Python ≥3.10 in an isolated venv:
```bash
python -m venv .venv && source .venv/bin/activate
make dev
```
Copy the template env file and define `WEB3_RPC_URL`, `OPENAI_API_KEY`, and optionally `ENCRYPT_KEY`. If `ENCRYPT_KEY` is omitted, the CLI provisions `agentvault_store.key`; do not commit that key or `agentvault_store.json`.

## Build, Test & QA Commands
- `make dev` installs runtime + dev extras (pytest, asyncio, MCP tooling).
- `make test` runs `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` to avoid plugin clashes; filter with `-k` when iterating.
- `python -m agentvault_mcp.server` launches the MCP server; `agentvault <tool>` provides the same functionality via CLI.
- `make build`, `make upload-test`, and `make upload` handle packaging; prune `dist/` before rebuilding.
- Release helpers live in `scripts/build.sh` and `scripts/tag_version.sh`; sync versions with `pyproject.toml`.

## Coding Standards & Patterns
Adopt PEP 8 with 4-space indentation, descriptive type hints, and snake_case modules. Guard optional imports (for example `tiktoken`, UI extras) with try/except fallbacks as shown in `core.py`. Use `structlog.get_logger` and emit structured fields instead of ad-hoc prints. Pydantic models should validate inputs via `field_validator`, and async tool handlers should be verbs (`micro_tip_equal`) returning serializable payloads.

## Testing Practices
Add tests following the `test_<feature>.py` convention at repo root. Leverage `pytest` and `pytest-asyncio` for coroutine coverage. Fixture setup should point wallets to disposable stores (configure `AGENTVAULT_STORE_PATH` or tmp dirs) and mock RPC endpoints. Capture guardrail regressions before extending wallet, server, or strategy APIs, and sanitize transaction data in fixtures.

## Commit & PR Workflow
Commits follow Conventional Commits (`feat`, `fix`, `docs`) with ≤72 character subjects. Document test evidence or manual verification in PR descriptions, link issues, and flag new env vars or migration steps. Security-sensitive modifications (wallet persistence, encryption flows, adapters) need reviewer acknowledgment and a brief operational impact statement.

## Security & Operational Checks
Never commit generated secrets, temporary dashboards, or key material. Keep `.env`, `agentvault_store.*`, and HTML previews in `.gitignore`. Verify new adapters degrade gracefully when credentials are missing and respect the policies enforced by `guardrail.py`. When sharing logs or traces, redact wallet addresses and transaction hashes.
