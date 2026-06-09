# Demo pack

LLM Meter includes a deterministic demo generator so you can evaluate the project without exposing real gateway logs.

```bash
python3 -m llm_meter demo --output-dir /tmp/llm-meter-demo
```

It writes:

```text
/tmp/llm-meter-demo/
├── demo-gateway.jsonl   # sanitized OpenAI-compatible gateway sample logs
├── demo.db              # SQLite database created from the sample logs
├── demo-report.html     # static dashboard report for browsers
└── demo-report.zip      # shareable bundle for issues, handoff, or status notes
```

## What the demo shows

The generated data intentionally covers the core observability surfaces:

- request volume over time
- 2xx / 4xx / 5xx status mix
- top IPs, paths, methods, hosts, and auth prefixes
- model usage
- prompt / completion / total tokens
- estimated cost in USD
- slow-request and error/rate-limit signals

The timestamps, models, IPs, token counts, and costs are deterministic. Running the command twice with the same `--rows` value produces the same JSONL fixture, which makes it useful for tests, screenshots, and docs.

## Open the HTML report

```bash
python3 -m llm_meter demo --output-dir /tmp/llm-meter-demo
xdg-open /tmp/llm-meter-demo/demo-report.html
```

On a headless VPS, copy the file to your workstation or serve it locally:

```bash
cd /tmp/llm-meter-demo
python3 -m http.server 8000
# open http://127.0.0.1:8000/demo-report.html through your tunnel / SSH port forward
```

## Inspect the share bundle

```bash
unzip -l /tmp/llm-meter-demo/demo-report.zip
```

Expected contents:

```text
manifest.json
report.html
report.json
report.md
```

Use this ZIP when you want to attach a reproducible report to a GitHub issue, incident note, support request, or chat handoff without sharing real production logs.

## Change the demo size

```bash
python3 -m llm_meter demo --output-dir /tmp/llm-meter-demo --rows 240
```

More rows create a denser trend line while preserving deterministic output.

## Safety note

The demo uses documentation-only IP ranges such as `203.0.113.0/24`, fake auth prefixes, and synthetic model/cost data. It is safe to commit screenshots or generated reports from the demo, but do not commit reports generated from your real gateway logs unless you have reviewed IPs, paths, and auth prefixes.
