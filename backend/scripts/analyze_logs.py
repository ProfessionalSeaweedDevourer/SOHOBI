"""
SOHOBI 성능 분석 스크립트

사용법:
  python scripts/analyze_logs.py                          # 로컬 JSONL 전체 분석
  python scripts/analyze_logs.py --remote                 # API에서 직접 조회
  python scripts/analyze_logs.py --since 2026-04-07       # 특정 기간
  python scripts/analyze_logs.py --compare 2026-04-07     # before/after 비교

사전 준비 (로컬 모드):
  python scripts/pull_logs.py                             # 원격 → 로컬 동기화
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

LOGS_DIR = Path(
    os.environ.get("LOGS_DIR", Path(__file__).parent.parent / "logs" / "remote")
)


# ── 데이터 로드 ────────────────────────────────────────────────────


def _load_local(log_type: str = "queries") -> list[dict]:
    path = LOGS_DIR / f"{log_type}.jsonl"
    if not path.exists():
        print(f"  파일 없음: {path}")
        print("  힌트: python scripts/pull_logs.py 로 먼저 동기화하세요.")
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _load_remote(log_type: str = "queries") -> list[dict]:
    host = os.environ.get("BACKEND_HOST", "")
    api_key = os.environ.get("API_SECRET_KEY", "")
    if not host or not api_key:
        print("오류: BACKEND_HOST / API_SECRET_KEY 환경변수가 필요합니다.")
        sys.exit(1)
    url = f"{host.rstrip('/')}/api/v1/logs"
    r = requests.get(
        url,
        params={"type": log_type, "limit": 0},
        headers={"X-API-Key": api_key},
        timeout=60,
    )
    if r.status_code != 200:
        print(f"오류: HTTP {r.status_code} — {r.text[:200]}")
        sys.exit(1)
    return r.json().get("entries", [])


# ── 통계 계산 ──────────────────────────────────────────────────────


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(int(len(sorted_vals) * p), len(sorted_vals) - 1)]


def compute_stats(entries: list[dict]) -> dict:
    latencies = sorted(e["latency_ms"] for e in entries if e.get("latency_ms"))
    n = len(latencies)  # noqa: F841

    by_domain: dict[str, list[float]] = defaultdict(list)
    by_status: dict[str, int] = defaultdict(int)
    by_grade: dict[str, int] = defaultdict(int)
    for e in entries:
        if e.get("latency_ms"):
            by_domain[e.get("domain", "unknown")].append(e["latency_ms"])
        by_status[e.get("status", "unknown")] += 1
        grade = e.get("grade", "")
        if grade:
            by_grade[grade] += 1

    def lat_stats(lats: list[float]) -> dict:
        lats.sort()
        ln = len(lats)
        return {
            "n": ln,
            "avg": sum(lats) / ln / 1000 if ln else 0,
            "p50": _pct(lats, 0.5) / 1000,
            "p90": _pct(lats, 0.9) / 1000,
            "max": lats[-1] / 1000 if lats else 0,
        }

    return {
        "n": len(entries),
        "overall": lat_stats(latencies),
        "by_domain": {
            d: lat_stats(sorted(lats)) for d, lats in sorted(by_domain.items())
        },
        "by_status": dict(by_status),
        "by_grade": dict(by_grade),
    }


def compute_hourly(entries: list[dict]) -> list[tuple[str, int, float]]:
    hourly: dict[str, list[float]] = defaultdict(list)
    for e in entries:
        ts = e.get("ts", "")[:13]  # YYYY-MM-DDTHH
        lat = e.get("latency_ms")
        if ts and lat:
            hourly[ts].append(lat)
    return [
        (h, len(lats), sum(lats) / len(lats) / 1000)
        for h, lats in sorted(hourly.items())
    ]


def top_slow(entries: list[dict], n: int = 5) -> list[dict]:
    with_lat = [e for e in entries if e.get("latency_ms")]
    with_lat.sort(key=lambda e: e["latency_ms"], reverse=True)
    return with_lat[:n]


# ── 출력 ───────────────────────────────────────────────────────────


def print_report(
    stats: dict, title: str = "", entries: list[dict] | None = None
) -> None:
    o = stats["overall"]
    hdr = title or "SOHOBI 성능 리포트"
    print(f"\n{'═' * 50}")
    print(f"  {hdr}")
    print(f"{'═' * 50}")
    print(
        f"\n전체: n={o['n']}  avg={o['avg']:.1f}s  p50={o['p50']:.1f}s  p90={o['p90']:.1f}s  max={o['max']:.1f}s"
    )

    print("\n── 에이전트별 ──")
    for domain, ds in stats["by_domain"].items():
        print(
            f"  {domain:12s}  n={ds['n']:3d}  avg={ds['avg']:5.1f}s  p50={ds['p50']:5.1f}s  p90={ds['p90']:5.1f}s  max={ds['max']:5.1f}s"
        )

    print("\n── 등급/상태 ──")
    total = stats["n"]
    status_parts = [
        f"{k}: {v} ({v / total * 100:.1f}%)"
        for k, v in sorted(stats["by_status"].items())
    ]
    print(f"  {', '.join(status_parts)}")
    grade_parts = [
        f"Grade {k}: {v} ({v / total * 100:.1f}%)"
        for k, v in sorted(stats["by_grade"].items())
    ]
    print(f"  {', '.join(grade_parts)}")

    if entries:
        hourly = compute_hourly(entries)
        if hourly:
            print("\n── 시간대별 추이 ──")
            for h, hn, havg in hourly:
                day_hour = h[5:].replace("T", " ") + "시"
                print(f"  {day_hour}  n={hn:3d}  avg={havg:5.1f}s")

        slow = top_slow(entries)
        if slow:
            print("\n── 느린 요청 TOP 5 ──")
            for i, e in enumerate(slow, 1):
                q = e.get("question", "")[:40]
                print(
                    f'  {i}. {e["latency_ms"] / 1000:.1f}s  {e.get("domain", "?"):8s}  "{q}..."'
                )

    print()


def print_comparison(before: dict, after: dict) -> None:
    print(f"\n{'═' * 60}")
    print("  Before / After 비교")
    print(f"{'═' * 60}")
    print(f"\n{'':18s} {'Before':>14s}  {'After':>14s}  {'변화':>8s}")
    print(f"  {'─' * 54}")

    def row(label: str, bval: float, aval: float) -> None:
        if bval == 0:
            pct = "—"
        else:
            diff = (aval - bval) / bval * 100
            pct = f"{diff:+.1f}%"
        print(f"  {label:16s} {bval:12.1f}s  {aval:12.1f}s  {pct:>8s}")

    bo, ao = before["overall"], after["overall"]
    row("전체 avg", bo["avg"], ao["avg"])
    row("전체 p50", bo["p50"], ao["p50"])
    row("전체 p90", bo["p90"], ao["p90"])
    row("전체 max", bo["max"], ao["max"])

    all_domains = sorted(set(before["by_domain"]) | set(after["by_domain"]))
    for d in all_domains:
        bd = before["by_domain"].get(d, {"avg": 0, "n": 0})
        ad = after["by_domain"].get(d, {"avg": 0, "n": 0})
        row(f"{d} avg", bd["avg"], ad["avg"])

    print()


# ── 필터 ───────────────────────────────────────────────────────────


def filter_by_date(entries: list[dict], since: str = "", until: str = "") -> list[dict]:
    result = entries
    if since:
        result = [e for e in result if e.get("ts", "") >= since]
    if until:
        next_day = (date.fromisoformat(until) + timedelta(days=1)).isoformat()
        result = [e for e in result if e.get("ts", "") < next_day]
    return result


# ── main ───────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="SOHOBI 성능 분석")
    parser.add_argument(
        "--remote", action="store_true", help="로컬 JSONL 대신 API에서 직접 조회"
    )
    parser.add_argument("--since", default="", help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--until", default="", help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument(
        "--compare", default="", help="기준일 (YYYY-MM-DD) — before/after 비교"
    )
    parser.add_argument(
        "--dir", default="", help="로컬 JSONL 디렉토리 (기본값: logs/remote)"
    )
    args = parser.parse_args()

    global LOGS_DIR
    if args.dir:
        LOGS_DIR = Path(args.dir)

    load = _load_remote if args.remote else _load_local
    entries = load("queries")
    if not entries:
        print("분석할 로그가 없습니다.")
        sys.exit(0)

    if args.compare:
        before = filter_by_date(entries, since=args.since, until=args.compare)
        after = filter_by_date(entries, since=args.compare, until=args.until)
        if not before or not after:
            print(f"비교 불가: before={len(before)}건, after={len(after)}건")
            sys.exit(1)
        bs = compute_stats(before)
        as_ = compute_stats(after)
        print_report(bs, f"Before ({args.compare} 이전, n={bs['n']})", before)
        print_report(as_, f"After ({args.compare} 이후, n={as_['n']})", after)
        print_comparison(bs, as_)
    else:
        filtered = filter_by_date(entries, args.since, args.until)
        if not filtered:
            print("해당 기간에 로그가 없습니다.")
            sys.exit(0)
        stats = compute_stats(filtered)
        period = ""
        if args.since or args.until:
            period = f" ({args.since or '처음'} ~ {args.until or '현재'})"
        print_report(stats, f"SOHOBI 성능 리포트{period}", filtered)


if __name__ == "__main__":
    main()
