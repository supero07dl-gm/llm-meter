import csv
import subprocess
import sys

from llm_meter.csv_export import export_csv
from llm_meter.storage import ingest_lines


def _seed_db(db):
    ingest_lines(
        [
            '{"timestamp":"2026-06-09T00:00:00Z","ip":"203.0.113.10","host":"api.example","method":"POST","path":"/v1/chat/completions","status":200,"auth_prefix":"sk-live-","request_time_ms":250,"model":"gpt-4o-mini","prompt_tokens":100,"completion_tokens":50,"total_tokens":150,"cost_usd":0.0000675}',
            '{"timestamp":"2026-06-09T00:05:00Z","ip":"198.51.100.23","host":"api.example","method":"GET","path":"/v1/models","status":429,"auth_prefix":"-","request_time_ms":100,"model":"-","prompt_tokens":0,"completion_tokens":0,"total_tokens":0,"cost_usd":0}',
        ],
        db,
    )


def test_export_csv_writes_entries(tmp_path):
    db = tmp_path / "meter.db"
    output = tmp_path / "entries.csv"
    _seed_db(db)

    result = export_csv(db, output)

    assert result == {"output": str(output), "rows": 2}
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["ts"] == "2026-06-09T00:00:00+00:00"
    assert rows[0]["ip"] == "203.0.113.10"
    assert rows[0]["status"] == "200"
    assert rows[0]["model"] == "gpt-4o-mini"
    assert rows[0]["total_tokens"] == "150"
    assert rows[0]["cost_usd"] == "6.75e-05"
    assert rows[1]["status"] == "429"


def test_export_csv_cli(tmp_path):
    db = tmp_path / "meter.db"
    output = tmp_path / "entries.csv"
    _seed_db(db)

    proc = subprocess.run(
        [sys.executable, "-m", "llm_meter", "export-csv", "--db", str(db), "--output", str(output), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    assert '"rows": 2' in proc.stdout
    assert output.exists()
