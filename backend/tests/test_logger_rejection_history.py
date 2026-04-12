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

    def test_severity_none_when_missing(self):
        history = [
            {
                "attempt": 1,
                "verdict": {
                    "issues": [{"code": "F1", "reason": "x"}],
                },
            }
        ]
        out = _format_rejection_history(history)
        assert out[0]["issues"][0]["severity"] is None

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
