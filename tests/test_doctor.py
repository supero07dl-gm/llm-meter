from llm_meter.doctor import run_doctor
from llm_meter.storage import ingest_lines


def test_doctor_reports_ok_for_valid_deployment(tmp_path):
    db = tmp_path / "meter.db"
    log = tmp_path / "gateway.log"
    config = tmp_path / "llm-meter.yml"
    log.write_text(
        '203.0.113.10 realip=- cf=- host=a.example auth_prefix=a [09/Jun/2026:02:00:01 +0000] "GET /v1/models HTTP/2.0" 200 1 rt=0.1 uct=0.01 urt=0.09 "-" "curl"\n',
        encoding="utf-8",
    )
    ingest_lines(log.read_text(encoding="utf-8").splitlines(), db)
    config.write_text(
        f"""
database: {db}
retention_days: 30
alert:
  rules:
    max_4xx_rate: 0.3
""".strip(),
        encoding="utf-8",
    )

    result = run_doctor(db_path=db, config_path=config, log_path=log)

    assert result["ok"] is True
    assert all(check["status"] == "ok" for check in result["checks"])


def test_doctor_warns_about_missing_inputs_and_empty_db(tmp_path):
    db = tmp_path / "empty.db"
    result = run_doctor(db_path=db, config_path=tmp_path / "missing.yml", log_path=tmp_path / "missing.log")

    assert result["ok"] is False
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    assert statuses["config"] == "fail"
    assert statuses["database"] == "warn"
    assert statuses["log"] == "fail"


def test_doctor_text_is_human_readable(tmp_path):
    from llm_meter.doctor import format_doctor_text

    result = run_doctor(db_path=tmp_path / "missing.db")
    text = format_doctor_text(result)

    assert "LLM Meter doctor" in text
    assert "database" in text
    assert "WARN" in text
