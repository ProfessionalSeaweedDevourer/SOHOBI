"""_format_rejection_history severity 필드 보존 테스트.

실행:
    cd backend
    .venv/bin/python -m pytest tests/test_logger_rejection_history.py -v
"""

from logger import _format_rejection_history


class TestRejectionHistoryFormatting:
    def test_severity_preserved_in_issues(self):
        history = [
            {
                "attempt": 1,
                "verdict": {
                    "approved": False,
                    "grade": "B",
                    "issues": [
                        {"code": "F2", "severity": "low", "reason": "단위 누락"},
                    ],
                },
            }
        ]
        out = _format_rejection_history(history)
        assert out[0]["issues"][0]["severity"] == "low"
        assert out[0]["issues"][0]["code"] == "F2"
        assert out[0]["issues"][0]["reason"] == "단위 누락"

    def test_severity_defaults_to_high_when_missing(self):
        history = [
            {
                "attempt": 1,
                "verdict": {
                    "issues": [{"code": "F1", "reason": "x"}],
                },
            }
        ]
        out = _format_rejection_history(history)
        assert out[0]["issues"][0]["severity"] == "high"

    def test_double_format_collapses_verdict_fields(self):
        """이미 flatten된 엔트리를 다시 포맷하면 verdict 필드가 소실됨을 보장.

        api_server.py 스트림 핸들러가 raw 데이터를 log_query에 넘기도록 유지하기
        위한 회귀 테스트. log_query 내부에서 _format_rejection_history를 호출하므로
        호출부에서 사전 포맷한 값을 넘기면 grade/issues 등이 공값으로 기록된다.
        """
        raw = [
            {
                "attempt": 1,
                "verdict": {
                    "approved": False,
                    "grade": "B",
                    "issues": [{"code": "F2", "severity": "low", "reason": "x"}],
                },
            }
        ]
        once = _format_rejection_history(raw)
        twice = _format_rejection_history(once)
        assert once[0]["grade"] == "B"
        assert once[0]["issues"][0]["severity"] == "low"
        assert twice[0]["grade"] == ""
        assert twice[0]["issues"] == []

    def test_all_severity_levels_round_trip(self):
        history = [
            {
                "attempt": 1,
                "verdict": {
                    "issues": [
                        {"code": "C1", "severity": "high", "reason": "r1"},
                        {"code": "A2", "severity": "medium", "reason": "r2"},
                        {"code": "C5", "severity": "low", "reason": "r3"},
                    ],
                },
            }
        ]
        out = _format_rejection_history(history)
        severities = [i["severity"] for i in out[0]["issues"]]
        assert severities == ["high", "medium", "low"]
