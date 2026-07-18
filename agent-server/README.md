# Agent Server

The server keeps DeepSeek credentials out of draw.io and converts model output through a validated Diagram IR before rendering native `mxCell` XML.

From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
# export values from .env with your preferred environment manager
.venv/bin/uvicorn app.main:app --app-dir agent-server --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/docs` for the local API documentation. Without a key, the development default returns an explicitly labeled deterministic draft. Set `TEXT2DRAWIO_ALLOW_OFFLINE_FALLBACK=false` in production.
