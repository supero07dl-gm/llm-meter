import json

from llm_meter.analyzer import analyze_lines
from llm_meter.storage import ingest_lines, report_from_db


def test_json_logs_extract_model_tokens_and_cost():
    report = analyze_lines([
        json.dumps({
            "timestamp": "2026-06-09T02:00:00Z",
            "ip": "203.0.113.10",
            "host": "api.example",
            "method": "POST",
            "path": "/v1/chat/completions",
            "status": 200,
            "model": "gpt-4o-mini",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
            "cost_usd": 0.000675,
        }),
        json.dumps({
            "timestamp": "2026-06-09T02:01:00Z",
            "ip": "198.51.100.23",
            "host": "api.example",
            "method": "POST",
            "path": "/v1/chat/completions",
            "status": 200,
            "model": "gpt-4o-mini",
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
            "cost_usd": 0.000135,
        }),
    ])

    payload = report.to_dict()
    assert payload["tokens"] == {"prompt": 1200, "completion": 600, "total": 1800}
    assert payload["cost"]["total_usd"] == 0.00081
    assert payload["models"] == {"gpt-4o-mini": 2}
    assert payload["cost"]["by_model"] == {"gpt-4o-mini": 0.00081}


def test_sqlite_report_preserves_cost_fields(tmp_path):
    db = tmp_path / "meter.db"
    ingest_lines([
        json.dumps({
            "timestamp": "2026-06-09T02:00:00Z",
            "ip": "203.0.113.10",
            "host": "api.example",
            "method": "POST",
            "path": "/v1/chat/completions",
            "status": 200,
            "model": "claude-3-5-sonnet",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "cost": 0.0012,
        })
    ], db)

    payload = report_from_db(db).to_dict()
    assert payload["tokens"] == {"prompt": 10, "completion": 20, "total": 30}
    assert payload["cost"]["total_usd"] == 0.0012
    assert payload["models"] == {"claude-3-5-sonnet": 1}
