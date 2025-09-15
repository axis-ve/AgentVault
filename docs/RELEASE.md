# Release Guide (v0.1.0)

## Prerequisites
- Python 3.10+ (3.13 supported)
- Latest pip: `pip install --upgrade pip`
- Build tools: `pip install -e .[release]`
- Git configured and clean working tree

## Sanity Checks
```bash
make dev
make test
agentvault --help
python -m agentvault_mcp.server  # ensure server starts
```

## Build Artifacts
```bash
make build
ls dist/
```

## Upload to TestPyPI (recommended first)
```bash
make upload-test
# Test install (new venv)
pip install -i https://test.pypi.org/simple/ agentvault-mcp
```

## Upload to PyPI
```bash
make upload
```

## Tag Release
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Post-Release
- Update README badges (downloads, version) if desired
- Announce: include zero‑setup demo steps and tip‑jar/dashboard screenshots

