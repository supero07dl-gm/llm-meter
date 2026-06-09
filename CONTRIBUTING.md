# Contributing

Thanks for helping improve LLM Meter.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip pytest build
pytest -q
python -m llm_meter analyze examples/cpa.log
```

## Good first contributions

- Add a parser fixture for your gateway log format.
- Improve Nginx / Cloudflare examples.
- Add docs for LiteLLM, OneAPI/NewAPI, LocalAI, Ollama gateways.
- Improve abuse signal heuristics.
- Add dashboard mockups.

## Safety rules

- Do not commit real access logs.
- Do not commit API keys.
- If a fixture needs Authorization data, use fake prefixes only.
- Prefer logging short key prefixes, never full tokens.

## Release checklist

```bash
pytest -q
python -m build
git tag vX.Y.Z
git push origin main vX.Y.Z
```
