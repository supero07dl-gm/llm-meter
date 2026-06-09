# systemd deployment

This directory provides example units for running LLM Meter continuously on a VPS:

- `llm-meter-ingest.service` — follows an Nginx access log and writes to SQLite
- `llm-meter-dashboard.service` — serves the local web dashboard
- `llm-meter-prometheus.service` — exposes `/metrics` for Prometheus

## Install

Build/install LLM Meter first:

```bash
python3 -m pip install llm-meter
# or from a checkout:
python3 -m pip install .
```

Prepare data directory:

```bash
sudo install -d -o www-data -g www-data /var/lib/llm-meter
```

Copy units:

```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llm-meter-ingest.service
sudo systemctl enable --now llm-meter-dashboard.service
sudo systemctl enable --now llm-meter-prometheus.service
```

Check:

```bash
systemctl status llm-meter-ingest llm-meter-dashboard llm-meter-prometheus --no-pager
curl http://127.0.0.1:8765/healthz
curl http://127.0.0.1:9108/metrics
```

## Customize

Edit these values before enabling the services:

- log file path: `/var/log/nginx/llm-gateway-access.log`
- database path: `/var/lib/llm-meter/llm-meter.db`
- listen address and ports
- service user/group

The example units use conservative hardening options. If your logs or database live elsewhere, update `ReadOnlyPaths` and `ReadWritePaths`.
