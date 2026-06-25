from llm_meter.parser import _parse_json_time, parse_line
from llm_meter.analyzer import analyze_lines


def test_parse_json_time_handles_nanosecond_timestamp():
    # Nanosecond timestamp for 2024-01-15 12:00:00 UTC:
    # 1705312800000000000 ns
    dt = _parse_json_time(1_705_312_800_000_000_000)
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15


def test_parse_json_time_handles_millisecond_timestamp():
    # Millisecond timestamp for 2024-01-15 12:00:00 UTC:
    # 1705312800000 ms
    dt = _parse_json_time(1_705_312_800_000)
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15


def test_parse_json_time_handles_second_timestamp():
    # Second timestamp for 2024-01-15 12:00:00 UTC: 1705312800
    dt = _parse_json_time(1_705_312_800)
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15


def test_parse_cpa_combined_log_line():
    line = (
        '203.0.113.10 realip=172.71.1.1 cf=203.0.113.10 '
        'host=api.example.com auth_prefix=sk-live- '
        '[09/Jun/2026:02:00:01 +0000] "POST /v1/chat/completions HTTP/2.0" '
        '200 1234 rt=1.234 uct=0.001 urt=1.230 "-" "curl/8"'
    )
    entry = parse_line(line)
    assert entry is not None
    assert entry.ip == "203.0.113.10"
    assert entry.host == "api.example.com"
    assert entry.auth_prefix == "sk-live-"
    assert entry.method == "POST"
    assert entry.path == "/v1/chat/completions"
    assert entry.status == 200
    assert entry.request_time == 1.234
    assert entry.upstream_response_time == 1.230


def test_parse_common_combined_log_line():
    line = '198.51.100.23 - - [09/Jun/2026:02:00:02 +0000] "GET /v1/models HTTP/1.1" 401 27 "-" "curl/8"'
    entry = parse_line(line)
    assert entry is not None
    assert entry.ip == "198.51.100.23"
    assert entry.method == "GET"
    assert entry.path == "/v1/models"
    assert entry.status == 401


def test_parse_cloudflare_logpush_json_line():
    line = '{"ClientIP":"203.0.113.10","ClientRequestHost":"api.example.com","ClientRequestMethod":"POST","ClientRequestURI":"/v1/chat/completions","ClientRequestProtocol":"HTTP/2","EdgeResponseStatus":200,"EdgeResponseBytes":1234,"EdgeStartTimestamp":"2026-06-09T02:00:01Z","OriginResponseDurationMs":1234}'
    entry = parse_line(line)
    assert entry is not None
    assert entry.ip == "203.0.113.10"
    assert entry.cf == "203.0.113.10"
    assert entry.host == "api.example.com"
    assert entry.method == "POST"
    assert entry.path == "/v1/chat/completions"
    assert entry.status == 200
    assert entry.body_bytes == 1234
    assert entry.request_time == 1.234


def test_analyze_lines_counts_status_and_ips():
    lines = [
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=aaaa1111 [09/Jun/2026:02:00:01 +0000] "POST /v1/chat/completions HTTP/2.0" 200 123 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=aaaa1111 [09/Jun/2026:02:00:02 +0000] "POST /v1/chat/completions HTTP/2.0" 429 12 rt=0.2 uct=0.01 urt=0.19 "-" "curl"',
        '198.51.100.23 - - [09/Jun/2026:02:00:03 +0000] "GET /v1/models HTTP/1.1" 401 27 "-" "curl"',
        'not a log line',
    ]
    report = analyze_lines(lines)
    assert report.total == 4
    assert report.parsed == 3
    assert report.failed == 1
    assert report.statuses[200] == 1
    assert report.statuses[429] == 1
    assert report.statuses[401] == 1
    assert report.ips["203.0.113.10"] == 2
