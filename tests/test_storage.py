from llm_meter.storage import hourly_counts, ingest_lines, report_from_db


def test_ingest_and_report_sqlite(tmp_path):
    db = tmp_path / "meter.db"
    lines = [
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=aaaa1111 [09/Jun/2026:02:00:01 +0000] "POST /v1/chat/completions HTTP/2.0" 200 123 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
        '198.51.100.23 realip=- cf=- host=a.example auth_prefix=- [09/Jun/2026:03:00:02 +0000] "GET /v1/models HTTP/2.0" 401 27 rt=0.2 uct=0.01 urt=0.19 "-" "curl"',
        'bad line',
    ]

    result = ingest_lines(lines, db)
    assert result == {"parsed": 2, "failed": 1, "inserted": 2}

    report = report_from_db(db)
    assert report.parsed == 2
    assert report.statuses[200] == 1
    assert report.statuses[401] == 1
    assert report.ips["203.0.113.10"] == 1

    trend = hourly_counts(db)
    assert trend == [
        {"hour": "2026-06-09T02", "requests": 1, "ok": 1, "client_errors": 0, "server_errors": 0},
        {"hour": "2026-06-09T03", "requests": 1, "ok": 0, "client_errors": 1, "server_errors": 0},
    ]


def test_report_limit_uses_newest_rows(tmp_path):
    db = tmp_path / "meter.db"
    lines = [
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:01 +0000] "GET /old HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
        '203.0.113.11 realip=- cf=- host=a.example auth_prefix=b [09/Jun/2026:02:00:02 +0000] "GET /new HTTP/2.0" 429 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"',
    ]
    ingest_lines(lines, db)
    report = report_from_db(db, limit=1)
    assert report.parsed == 1
    assert report.paths["/new"] == 1
    assert report.statuses[429] == 1
