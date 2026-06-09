# Gateway presets

LLM Meter is gateway-agnostic. It reads access logs, so the easiest integration path is to put Nginx or another reverse proxy in front of your OpenAI-compatible endpoint and use the `llm_gateway` log format from [docs/nginx.md](nginx.md).

This page lists practical presets for common self-hosted LLM gateways.

## LiteLLM

LiteLLM exposes OpenAI-compatible endpoints such as `/v1/chat/completions`, `/v1/completions`, `/v1/models`, and provider-specific routes.

Recommended Nginx location:

```nginx
server {
    listen 443 ssl http2;
    server_name litellm.example.com;

    access_log /var/log/nginx/litellm-access.log llm_gateway;

    location / {
        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
        proxy_connect_timeout 60;
    }
}
```

Analyze:

```bash
llm-meter analyze /var/log/nginx/litellm-access.log
llm-meter ingest /var/log/nginx/litellm-access.log --db llm-meter.db --follow
```

## OneAPI / NewAPI

OneAPI and NewAPI commonly expose OpenAI-compatible routes and admin/UI pages from the same service. LLM Meter works best if you track `/v1/` traffic separately.

```nginx
server {
    listen 443 ssl http2;
    server_name newapi.example.com;

    access_log /var/log/nginx/newapi-access.log llm_gateway;

    location ^~ /v1/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Tip: if UI traffic is noisy, configure a separate `access_log off;` or a different log file for non-API paths.

## LocalAI

LocalAI usually listens on `:8080` and supports OpenAI-compatible endpoints.

```nginx
server {
    listen 443 ssl http2;
    server_name localai.example.com;

    access_log /var/log/nginx/localai-access.log llm_gateway;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 600;
        proxy_send_timeout 600;
    }
}
```

## Ollama-compatible reverse proxies

Ollama itself is not OpenAI-compatible by default, but many deployments expose an OpenAI-compatible layer in front of it. Track the OpenAI-compatible layer, not raw Ollama `/api/*` routes, if you want model/API usage patterns comparable with other gateways.

Common paths:

- `/v1/chat/completions`
- `/v1/completions`
- `/v1/models`
- `/api/chat` if you intentionally want raw Ollama traffic

## CLIProxyAPI

CLIProxyAPI deployments usually sit behind Nginx and expose `:8317` locally:

```bash
llm-meter ingest /var/log/nginx/cpa-access.log --db llm-meter.db --follow
llm-meter serve --db llm-meter.db
llm-meter export-prometheus --db llm-meter.db
```

## Privacy checklist

- Do not log full Authorization headers.
- Prefer `auth_prefix` with 8 characters or fewer.
- Do not commit real logs to GitHub.
- If sharing screenshots, redact IPs and key prefixes.
