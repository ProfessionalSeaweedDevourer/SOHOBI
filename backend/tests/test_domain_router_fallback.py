"""라우터 LLM 실패 시 키워드 단서 대체 테스트 (네트워크 불필요)."""

import asyncio
from unittest.mock import patch

import domain_router
from domain_router import _FALLBACK, classify


def _classify_with_llm_failure(question: str) -> dict:
    async def fail(*_args, **_kwargs):
        return _FALLBACK

    with patch.object(domain_router, "_llm_classify", fail):
        return asyncio.run(classify(question))


def test_single_location_keyword_beats_admin_default():
    # 2026-11-02 실제 오분류 질문. 키워드는 '상권' 하나뿐이라 키워드 분류를 건너뛴다.
    assert (
        _classify_with_llm_failure("삼성동 샐러드 상권은 어때?")["domain"] == "location"
    )


def test_no_keyword_keeps_admin_default():
    assert _classify_with_llm_failure("이거 어떻게 해야 하나요?") is _FALLBACK


def test_tied_keywords_keep_admin_default():
    # location '상권' 1개, legal '고소' 1개로 동률이면 단서로 쓰지 않는다
    result = _classify_with_llm_failure("상권 고소")
    assert result is _FALLBACK
