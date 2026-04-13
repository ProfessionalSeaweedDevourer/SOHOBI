"""log_query signoff_ms·final_verdict 스키마 확장 테스트.

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_logger_signoff_schema.py -v
"""

import json

import pytest


@pytest.fixture
def tmp_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path))
    monkeypatch.delenv("BLOB_LOGS_ACCOUNT", raising=False)

    import importlib

    import logger

    importlib.reload(logger)
    yield tmp_path / "queries.jsonl", logger
    importlib.reload(logger)


class TestQueriesSchemaExtension:
    def test_signoff_ms_recorded(self, tmp_logs):
        queries_log, logger = tmp_logs
        logger.log_query(
            request_id="r1",
            question="q",
            domain="chat",
            status="approved",
            grade="A",
            retry_count=0,
            rejection_history=[],
            draft="d",
            latency_ms=1234.5,
            signoff_ms=567.8,
        )
        record = json.loads(queries_log.read_text().strip())
        assert record["signoff_ms"] == 568
        assert record["final_verdict"] is None

    def test_final_verdict_normalized(self, tmp_logs):
        queries_log, logger = tmp_logs
        verdict = {
            "approved": True,
            "grade": "A",
            "passed": ["F1"],
            "warnings": [{"code": "W1", "reason": "minor", "extra": "drop"}],
            "issues": [{"code": "F2", "severity": "low", "reason": "r"}],
            "confidence_note": "ignored_field",
        }
        logger.log_query(
            request_id="r2",
            question="q",
            domain="finance",
            status="approved",
            grade="A",
            retry_count=0,
            rejection_history=[],
            draft="d",
            latency_ms=100,
            signoff_ms=200,
            final_verdict=verdict,
        )
        record = json.loads(queries_log.read_text().strip())
        fv = record["final_verdict"]
        assert fv["approved"] is True
        assert fv["grade"] == "A"
        assert fv["passed"] == ["F1"]
        assert fv["warnings"] == [{"code": "W1", "reason": "minor"}]
        assert fv["issues"] == [{"code": "F2", "severity": "low", "reason": "r"}]
        assert "confidence_note" not in fv

    def test_defaults_when_signoff_skipped(self, tmp_logs):
        queries_log, logger = tmp_logs
        logger.log_query(
            request_id="r3",
            question="q",
            domain="chat",
            status="approved",
            grade="A",
            retry_count=0,
            rejection_history=[],
            draft="d",
            latency_ms=50,
        )
        record = json.loads(queries_log.read_text().strip())
        assert record["signoff_ms"] == 0
        assert record["final_verdict"] is None
