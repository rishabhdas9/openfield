# Openfield

Openfield connects a Python dependency upgrade to the source usages and reviewed evidence that make the upgrade relevant.

The first slice covers HTTPX 0.27.2 to 0.28.0. It is intentionally narrow until its deterministic finding and evidence contract pass.

Run the local API on loopback after building the evidence database:

```bash
OPENFIELD_DATABASE=/tmp/openfield-evidence.db \
  uv run --extra web uvicorn openfield.api:app_from_environment \
  --factory --host 127.0.0.1 --port 8000
```
