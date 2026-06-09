# LLM Meter

**Lightweight usage analytics and abuse detection for OpenAI-compatible API gateways.**

LLM Meter turns plain access logs from Nginx / Cloudflare / self-hosted AI gateways into useful usage reports: request volume, status codes, top IPs, auth prefixes, model usage, latency, and possible abuse patterns.

It is designed for people running OpenAI-compatible API endpoints through tools like CLIProxyAPI, OneAPI/NewAPI, LiteLLM, LocalAI, Ollama-compatible gateways, or custom reverse proxies.

> MVP status: CLI log analyzer. Web dashboard, Prometheus exporter, and alerting are on the roadmap.

## Why

Self-hosted LLM API gateways are easy to expose, but hard to observe:

- Which IP is consuming the most requests?
- Are 401/429/5xx errors spiking?
- Which API key prefix is being abused?
- Are streaming requests getting slow?
- Did a public shared endpoint start attracting bot traffic?

LLM Meter starts with the boring, reliable source of truth: your gateway access logs.

## Features

- Parse Nginx-style logs, including custom fields like `host=`, `auth_prefix=`, `rt=`, `urt=`.
- Summarize total requests, status classes, hosts, paths, methods, top IPs, and auth prefixes.
- Detect common abuse signals:
  - high request count from one IP
  - many 401/429 responses
  - slow upstream responses
- Output human-readable text or JSON.
- Works locally, in Docker, or in CI.
- No database required for the first version.

## Quick start

```bash
python3 -m llm_meter analyze /var/log/nginx/tarai05-cpa-access.log
```

JSON output:

```bash
python3 -m llm_meter analyze /var/log/nginx/tarai05-cpa-access.log --json
```

Analyze only recent lines:

```bash
tail -n 5000 /var/log/nginx/tarai05-cpa-access.log | python3 -m llm_meter analyze -
```

Docker:

```bash
docker build -t llm-meter .
docker run --rm -v /var/log/nginx:/logs:ro llm-meter analyze /logs/tarai05-cpa-access.log
```

## Example output

```text
LLM Meter Report
================
Requests: 1280
Time range: 2026-06-09 01:00:00 -> 2026-06-09 02:00:00

Status classes:
  2xx  1120
  4xx  151
  5xx  9

Top IPs:
  203.0.113.10      502 req   39.2%
  198.51.100.23     188 req   14.7%

Top auth prefixes:
  sk-live-           610 req
  -                  151 req

Signals:
  WARN 203.0.113.10 accounts for 39.2% of traffic
  WARN 151 unauthorized/rate-limited requests
```

## Supported log format

LLM Meter works best with a log format like this:

```nginx
log_format cpa_combined '$remote_addr realip=$realip_remote_addr cf=$http_cf_connecting_ip '
                        'host=$host auth_prefix=$cpa_auth_prefix '
                        '[$time_local] "$request" $status $body_bytes_sent '
                        'rt=$request_time uct=$upstream_connect_time urt=$upstream_response_time '
                        '"$http_referer" "$http_user_agent"';
```

It also tries to parse common Nginx combined logs.

## Roadmap

- [ ] SQLite storage for historical trends
- [ ] Web dashboard
- [ ] Prometheus exporter
- [ ] Telegram / Discord / webhook alerts
- [ ] Cloudflare Logpush parser
- [ ] LiteLLM / OneAPI / NewAPI specific presets
- [ ] Docker Compose example
- [ ] Homebrew / PyPI package

## Project goals

- Minimal setup
- Safe-by-default log handling: do not store full API keys
- Useful for tiny VPS deployments and homelab AI gateways
- OpenAI-compatible, not vendor-specific

## License

MIT
