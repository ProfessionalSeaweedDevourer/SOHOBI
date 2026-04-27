#!/usr/bin/env python3
"""
Legal index pipeline — 3단계 (선택): 시행일·공포번호 메타 보강.

국가법령정보센터 OpenAPI: https://www.law.go.kr/DRF/lawService.do
- mst 별로 1회 조회 → 캐시
- enforceDate, promulgationNo, revisionType 부여

LAW_API_KEY 환경변수 미설정 시 단순 passthrough (다음 단계도 동작 보장).
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API_KEY = os.environ.get("LAW_API_KEY", "").strip()
API_URL = "https://www.law.go.kr/DRF/lawService.do"
CACHE_PATH = Path(".cache/law_metadata.sqlite")


def init_cache() -> sqlite3.Connection:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS law_meta (mst TEXT PRIMARY KEY, enforce_date TEXT, "
        "promulgation_no TEXT, revision_type TEXT, fetched_at INTEGER)"
    )
    conn.commit()
    return conn


def fetch_meta(mst: str) -> dict | None:
    if not API_KEY:
        return None
    params = {"OC": API_KEY, "target": "law", "MST": mst, "type": "XML"}
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(xml)
        return {
            "enforce_date": (root.findtext(".//시행일자") or "").strip(),
            "promulgation_no": (root.findtext(".//공포번호") or "").strip(),
            "revision_type": (root.findtext(".//제개정구분") or "").strip(),
        }
    except (OSError, ET.ParseError) as e:
        print(f"WARN: fetch failed for mst={mst}: {e}", file=sys.stderr)
        return None


def get_or_fetch(conn: sqlite3.Connection, mst: str) -> dict | None:
    cur = conn.execute(
        "SELECT enforce_date, promulgation_no, revision_type FROM law_meta WHERE mst=?",
        (mst,),
    )
    row = cur.fetchone()
    if row:
        return {
            "enforce_date": row[0],
            "promulgation_no": row[1],
            "revision_type": row[2],
        }

    meta = fetch_meta(mst)
    if meta:
        conn.execute(
            "INSERT OR REPLACE INTO law_meta VALUES (?, ?, ?, ?, ?)",
            (
                mst,
                meta["enforce_date"],
                meta["promulgation_no"],
                meta["revision_type"],
                int(time.time()),
            ),
        )
        conn.commit()
    return meta


def to_iso(date_str: str) -> str | None:
    s = date_str.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}T00:00:00Z"
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    if not API_KEY:
        print("LAW_API_KEY not set — passthrough mode (no enrichment)", file=sys.stderr)

    conn = init_cache() if API_KEY else None

    in_path = Path(args.input)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen_msts: set[str] = set()
    n = 0
    with (
        in_path.open(encoding="utf-8") as fin,
        out_path.open("w", encoding="utf-8") as fout,
    ):
        for line in fin:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            mst = r.get("mst", "")
            if conn and mst and mst not in seen_msts:
                seen_msts.add(mst)
                if len(seen_msts) % 5 == 0:
                    time.sleep(0.5)  # rate limit 보호
            if conn and mst:
                meta = get_or_fetch(conn, mst)
                if meta:
                    iso = to_iso(meta["enforce_date"])
                    if iso:
                        r["enforceDate"] = iso
                    if meta["promulgation_no"]:
                        r["promulgationNo"] = meta["promulgation_no"]
                    if meta["revision_type"]:
                        r["revisionType"] = meta["revision_type"]
            fout.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1

    print(f"enriched {n} records (unique laws fetched: {len(seen_msts)})")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
