"""
로그 포매터 — JSONL 로그를 사람이 읽기 편한 형태로 변환

사용법:
  # 전체 요청 로그 (기본)
  python log_formatter.py

  # 거부 이력만
  python log_formatter.py --type rejections

  # 최근 N건
  python log_formatter.py --limit 20

  # 마크다운 리포트 파일로 저장
  python log_formatter.py --output logs/report.md
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(os.environ.get("LOGS_DIR", Path(__file__).parent / "logs"))

DOMAIN_KR = {"finance": "재무", "admin": "행정", "legal": "법무"}
STATUS_ICON = {"approved": "✅", "escalated": "❌"}
PASS_COLOR = "✓"
FAIL_COLOR = "✗"


def _parse_jsonl_text(text: str) -> list[dict]:
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _load_jsonl(path: Path) -> list[dict]:
    """로컬 파일 또는 Blob Storage에서 JSONL을 읽는다."""
    account = os.environ.get("BLOB_LOGS_ACCOUNT", "")
    if account:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient
            from azure.core.exceptions import ResourceNotFoundError

            container = os.environ.get("BLOB_LOGS_CONTAINER", "sohobi-logs")
            service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=DefaultAzureCredential(),
            )
            blob_client = service.get_blob_client(container=container, blob=path.name)
            text = blob_client.download_blob().readall().decode("utf-8")
            return _parse_jsonl_text(text)
        except Exception:
            return []

    # 로컬 폴백
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return _parse_jsonl_text(f.read())


def _fmt_ts(ts_str: str) -> str:
    """ISO 타임스탬프 → 'YYYY-MM-DD HH:MM:SS' (로컬 시간)"""
    try:
        dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str


def _fmt_entry(entry: dict, index: int) -> str:
    lines = []
    sep = "─" * 60

    domain = entry.get("domain", "?")
    status = entry.get("status", "?")
    retry = entry.get("retry_count", 0)
    latency = entry.get("latency_ms", 0)
    ts = _fmt_ts(entry.get("ts", ""))
    question = entry.get("question", "")
    rejection_history = entry.get("rejection_history", [])

    status_icon = STATUS_ICON.get(status, "?")
    domain_kr = DOMAIN_KR.get(domain, domain)

    lines.append(sep)
    lines.append(
        f"[{index}] {ts}  |  {domain_kr}({domain})  |  "
        f"{status_icon} {status}  |  재시도 {retry}회  |  {latency:.0f}ms"
    )
    lines.append(f"Q: {question[:120]}{'...' if len(question) > 120 else ''}")

    if rejection_history:
        lines.append(f"\n  거부 이력 ({len(rejection_history)}회)")
        for attempt in rejection_history:
            a_num = attempt.get("attempt", "?")
            passed = attempt.get("passed", [])
            issues = attempt.get("issues", [])
            retry_prompt = attempt.get("retry_prompt", "")

            pass_str = " ".join(passed) if passed else "(없음)"
            lines.append(f"  ── 시도 {a_num}")
            lines.append(f"     {PASS_COLOR} 통과: {pass_str}")
            for issue in issues:
                code = issue.get("code", "?")
                reason = issue.get("reason", "")
                lines.append(f"     {FAIL_COLOR} 실패 {code}: {reason}")
            if retry_prompt:
                prompt_preview = retry_prompt[:200].replace("\n", " ")
                lines.append(f"     ↳ 수정 지시: {prompt_preview}{'...' if len(retry_prompt) > 200 else ''}")
    else:
        lines.append("  거부 이력 없음 (1회 통과)")

    return "\n".join(lines)


def _fmt_summary(entries: list[dict]) -> str:
    total = len(entries)
    approved = sum(1 for e in entries if e.get("status") == "approved")
    escalated = total - approved
    avg_latency = (
        sum(e.get("latency_ms", 0) for e in entries) / total if total else 0
    )
    avg_retry = (
        sum(e.get("retry_count", 0) for e in entries) / total if total else 0
    )

    domain_counts: dict[str, int] = {}
    for e in entries:
        d = e.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    lines = [
        "=" * 60,
        "SOHOBI 에이전트 로그 요약",
        f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        f"전체 요청: {total}건",
        f"  ✅ approved:  {approved}건 ({approved/total*100:.1f}%)" if total else "  데이터 없음",
        f"  ❌ escalated: {escalated}건 ({escalated/total*100:.1f}%)" if total else "",
        f"평균 응답 시간: {avg_latency:.0f}ms",
        f"평균 재시도: {avg_retry:.2f}회",
        "",
        "도메인별 요청 수:",
    ]
    for domain, count in sorted(domain_counts.items()):
        kr = DOMAIN_KR.get(domain, domain)
        lines.append(f"  {kr}({domain}): {count}건")

    return "\n".join(lines)


def _fmt_error_entry(entry: dict, index: int) -> str:
    sep = "─" * 60
    ts = _fmt_ts(entry.get("ts", ""))
    domain = entry.get("domain", "unknown")
    domain_kr = DOMAIN_KR.get(domain, domain)
    latency = entry.get("latency_ms", 0)
    question = entry.get("question", "")
    error = entry.get("error", "")
    lines = [
        sep,
        f"[{index}] {ts}  |  {domain_kr}({domain})  |  {latency:.0f}ms",
        f"Q: {question[:120]}{'...' if len(question) > 120 else ''}",
        f"오류: {error}",
    ]
    return "\n".join(lines)


def _fmt_error_summary(entries: list[dict]) -> str:
    total = len(entries)
    domain_counts: dict[str, int] = {}
    for e in entries:
        d = e.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1
    lines = [
        "=" * 60,
        "SOHOBI 응답 오류 로그 요약",
        f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        f"전체 오류: {total}건",
        "",
        "도메인별 오류 수:",
    ]
    for domain, count in sorted(domain_counts.items()):
        kr = DOMAIN_KR.get(domain, domain)
        lines.append(f"  {kr}({domain}): {count}건")
    return "\n".join(lines)


def format_logs(log_type: str = "queries", limit: int = 0) -> str:
    """로그를 포맷팅된 문자열로 반환. API 엔드포인트에서도 재사용."""
    path = LOGS_DIR / f"{log_type}.jsonl"
    entries = _load_jsonl(path)

    if not entries:
        return f"로그 파일이 없거나 비어 있습니다: {path}"

    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)

    if limit > 0:
        entries = entries[:limit]

    if log_type == "errors":
        output_parts = [_fmt_error_summary(entries), "\n\n상세 내역\n"]
        for i, entry in enumerate(entries, start=1):
            output_parts.append(_fmt_error_entry(entry, i))
        output_parts.append("─" * 60)
        return "\n".join(output_parts)

    output_parts = [_fmt_summary(entries)]
    output_parts.append("\n\n상세 내역\n")

    for i, entry in enumerate(entries, start=1):
        output_parts.append(_fmt_entry(entry, i))

    output_parts.append("─" * 60)
    return "\n".join(output_parts)


def load_entries_json(log_type: str = "queries", limit: int = 50) -> list[dict]:
    """API 엔드포인트용 — 파싱된 엔트리 리스트 반환. log_type: queries | rejections | errors"""
    path = LOGS_DIR / f"{log_type}.jsonl"
    entries = _load_jsonl(path)
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    if limit > 0:
        entries = entries[:limit]
    return entries


def main():
    parser = argparse.ArgumentParser(description="SOHOBI 로그 포매터")
    parser.add_argument(
        "--type",
        choices=["queries", "rejections", "errors"],
        default="queries",
        help="로그 파일 종류 (기본값: queries)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="출력할 최대 건수 (0=전체)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="출력 파일 경로 (미지정 시 표준 출력)",
    )
    args = parser.parse_args()

    result = format_logs(log_type=args.type, limit=args.limit)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"저장 완료: {out_path}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
