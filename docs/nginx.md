# Nginx setup for LLM Meter

LLM Meter works with normal Nginx combined logs, but a small custom log format gives much better gateway analytics.

## 1. Preserve real client IP behind Cloudflare

Create `/etc/nginx/conf.d/cloudflare-realip.conf` and keep Cloudflare ranges up to date:

```nginx
real_ip_header CF-Connecting-IP;
real_ip_recursive on;

# Example only. Use Cloudflare's current ranges in production.
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
```

## 2. Add a safe gateway log format

This format logs only a short API-key prefix. Never log full API keys.

```nginx
map $http_authorization $llm_auth_prefix {
    default "-";
    "~^Bearer\\s+(.{8}).*" $1;
    "~^(.{8}).*" $1;
}

log_format llm_gateway '$remote_addr realip=$realip_remote_addr cf=$http_cf_connecting_ip '
                       'host=$host auth_prefix=$llm_auth_prefix '
                       '[$time_local] "$request" $status $body_bytes_sent '
                       'rt=$request_time uct=$upstream_connect_time urt=$upstream_response_time '
                       '"$http_referer" "$http_user_agent"';
```

## 3. Use it on your OpenAI-compatible gateway

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    access_log /var/log/nginx/llm-gateway-access.log llm_gateway;

    location / {
        proxy_pass http://127.0.0.1:8317;
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
llm-meter analyze /var/log/nginx/llm-gateway-access.log
```
