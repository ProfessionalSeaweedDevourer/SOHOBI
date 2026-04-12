"""Sign-off severity 스키마 + _derive_grade 가중치 단위 테스트.

LLM 호출 없이 _derive_grade / _issue_severity / validate_verdict 순수 로직만 검증한다.

실행:
    cd integrated_PARK
    .venv/bin/python -m pytest tests/test_signoff_severity.py -v
"""

import pytest
from signoff.signoff_agent import (
    _derive_grade,
    _enforce_sec1_issue,
    _issue_severity,
    validate_verdict,
)


class TestIssueSeverity:
    def test_default_high_when_missing(self):
        assert _issue_severity({"code": "F1", "reason": "x"}) == "high"

    def test_explicit_low(self):
        assert (
            _issue_severity({"code": "F1", "reason": "x", "severity": "low"}) == "low"
        )

    def test_explicit_medium(self):
        assert (
            _issue_severity({"code": "F2", "reason": "x", "severity": "medium"})
            == "medium"
        )

    def test_invalid_severity_falls_back_to_high(self):
        assert (
            _issue_severity({"code": "F1", "reason": "x", "severity": "trivial"})
            == "high"
        )

    def test_non_dict_issue_defaults_high(self):
        assert _issue_severity("F1") == "high"

    def test_sec1_forced_high_regardless_of_severity(self):
        assert (
            _issue_severity({"code": "SEC1", "reason": "x", "severity": "low"})
            == "high"
        )

    def test_rj1_forced_high_regardless_of_severity(self):
        assert (
            _issue_severity({"code": "RJ1", "reason": "x", "severity": "low"}) == "high"
        )


class TestDeriveGrade:
    def test_no_issues_no_warnings_is_A(self):
        assert _derive_grade({"issues": [], "warnings": []}) == "A"

    def test_warnings_only_is_B(self):
        assert _derive_grade({"issues": [], "warnings": [{"code": "C1"}]}) == "B"

    def test_high_severity_issue_is_C(self):
        assert (
            _derive_grade(
                {"issues": [{"code": "F1", "severity": "high"}], "warnings": []}
            )
            == "C"
        )

    def test_medium_severity_issue_is_C(self):
        assert (
            _derive_grade(
                {"issues": [{"code": "F1", "severity": "medium"}], "warnings": []}
            )
            == "C"
        )

    def test_low_only_issue_is_B(self):
        assert (
            _derive_grade(
                {"issues": [{"code": "F1", "severity": "low"}], "warnings": []}
            )
            == "B"
        )

    def test_mixed_low_and_high_is_C(self):
        verdict = {
            "issues": [
                {"code": "F1", "severity": "low"},
                {"code": "F2", "severity": "high"},
            ],
            "warnings": [],
        }
        assert _derive_grade(verdict) == "C"

    def test_missing_severity_defaults_to_C(self):
        # 후방호환: severity 없으면 high로 간주 → C
        assert _derive_grade({"issues": [{"code": "F1"}], "warnings": []}) == "C"

    def test_sec1_forced_C_even_if_severity_low(self):
        assert (
            _derive_grade(
                {"issues": [{"code": "SEC1", "severity": "low"}], "warnings": []}
            )
            == "C"
        )

    def test_rj1_forced_C_even_if_severity_low(self):
        assert (
            _derive_grade(
                {"issues": [{"code": "RJ1", "severity": "low"}], "warnings": []}
            )
            == "C"
        )


class TestValidateVerdictGradeConsistency:
    def _base_finance_verdict(self):
        # finance 도메인 전체 커버리지를 passed로 채운 기본 verdict
        passed = [
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "SEC1",
            "SEC2",
            "SEC3",
            "RJ1",
            "RJ2",
            "RJ3",
        ]
        return {
            "approved": True,
            "grade": "A",
            "passed": passed,
            "warnings": [],
            "issues": [],
            "retry_prompt": "",
        }

    def test_A_grade_passes(self):
        verdict = self._base_finance_verdict()
        validate_verdict(verdict, "finance")

    def test_low_only_issue_with_B_grade_passes(self):
        verdict = self._base_finance_verdict()
        verdict["passed"].remove("F1")
        verdict["issues"] = [{"code": "F1", "severity": "low", "reason": "극단값 경미"}]
        verdict["approved"] = False
        verdict["grade"] = "B"
        verdict["retry_prompt"] = "개선 필요"
        validate_verdict(verdict, "finance")

    def test_low_only_issue_with_C_grade_fails(self):
        verdict = self._base_finance_verdict()
        verdict["passed"].remove("F1")
        verdict["issues"] = [{"code": "F1", "severity": "low", "reason": "경미"}]
        verdict["approved"] = False
        verdict["grade"] = "C"
        verdict["retry_prompt"] = "x"
        with pytest.raises(AssertionError, match="severity 기반 계산값"):
            validate_verdict(verdict, "finance")

    def test_high_issue_with_C_grade_passes(self):
        verdict = self._base_finance_verdict()
        verdict["passed"].remove("F1")
        verdict["issues"] = [{"code": "F1", "severity": "high", "reason": "심각"}]
        verdict["approved"] = False
        verdict["grade"] = "C"
        verdict["retry_prompt"] = "개선 필요"
        validate_verdict(verdict, "finance")


class TestSec1EnforcementKeepsGrade:
    def test_enforce_sec1_sets_grade_C(self):
        verdict = {
            "approved": True,
            "grade": "A",
            "passed": ["SEC1"],
            "warnings": [],
            "issues": [],
        }
        out = _enforce_sec1_issue(verdict, ["템플릿 라벨 노출"])
        assert out["grade"] == "C"
        assert out["approved"] is False
        assert any(
            i.get("code") == "SEC1" for i in out["issues"] if isinstance(i, dict)
        )

    def test_sec1_derived_grade_is_C_even_without_explicit_severity(self):
        # SEC1은 _FORCED_HIGH_CODES이므로 severity 없어도 C
        verdict = {
            "issues": [{"code": "SEC1", "reason": "누출"}],
            "warnings": [],
        }
        assert _derive_grade(verdict) == "C"
