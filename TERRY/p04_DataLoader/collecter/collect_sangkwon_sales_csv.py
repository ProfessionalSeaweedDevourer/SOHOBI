# =====================================================
# 서울 골목상권 매출 API 수집
# 위치: p04_DataLoader/collector/collect_sangkwon_sales_csv.py
# 결과: p04_DataLoader/csv/sangkwon_sales/sangkwon_{year}_utf8.csv
#
# 실행: python collector/collect_sangkwon_sales_csv.py 2025
#       python collector/collect_sangkwon_sales_csv.py 2024
#       python collector/collect_sangkwon_sales_csv.py 2025 4  ← 특정 분기만
# =====================================================

import requests
import csv
import time
import os
import sys

SANGKWON_KEY = "754877586377737436326350494f4c"
BASE_URL = f"http://openapi.seoul.go.kr:8088/{SANGKWON_KEY}/json/VwsmAdstrdSelngW"
PAGE_SIZE = 1000

# ── 경로 설정 (상대경로) ──────────────────────────────────────
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # p04_DataLoader/
OUTPUT_DIR = os.path.join(BASE_DIR, "csv", "sangkwon_sales")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── CSV 컬럼 ─────────────────────────────────────────────────
COLUMNS = [
    "기준_년분기_코드",
    "행정동_코드",
    "행정동_코드_명",
    "서비스_업종_코드",
    "서비스_업종_코드_명",
    "당월_매출_금액",
    "당월_매출_건수",
    "주중_매출_금액",
    "주말_매출_금액",
    "월요일_매출_금액",
    "화요일_매출_금액",
    "수요일_매출_금액",
    "목요일_매출_금액",
    "금요일_매출_금액",
    "토요일_매출_금액",
    "일요일_매출_금액",
    "남성_매출_금액",
    "여성_매출_금액",
    "연령대_10_매출_금액",
    "연령대_20_매출_금액",
    "연령대_30_매출_금액",
    "연령대_40_매출_금액",
    "연령대_50_매출_금액",
    "연령대_60_이상_매출_금액",
]

API_COLS = [
    "STDR_YYQU_CD",
    "ADSTRD_CD",
    "ADSTRD_CD_NM",
    "SVC_INDUTY_CD",
    "SVC_INDUTY_CD_NM",
    "THSMON_SELNG_AMT",
    "THSMON_SELNG_CO",
    "MDWK_SELNG_AMT",
    "WKEND_SELNG_AMT",
    "MON_SELNG_AMT",
    "TUES_SELNG_AMT",
    "WED_SELNG_AMT",
    "THUR_SELNG_AMT",
    "FRI_SELNG_AMT",
    "SAT_SELNG_AMT",
    "SUN_SELNG_AMT",
    "ML_SELNG_AMT",
    "FML_SELNG_AMT",
    "AGRDE_10_SELNG_AMT",
    "AGRDE_20_SELNG_AMT",
    "AGRDE_30_SELNG_AMT",
    "AGRDE_40_SELNG_AMT",
    "AGRDE_50_SELNG_AMT",
    "AGRDE_60_ABOVE_SELNG_AMT",
]


def fetch_page(start, end, retries=3):
    """API 1페이지 호출, 실패 시 재시도"""
    url = f"{BASE_URL}/{start}/{end}/"
    for attempt in range(retries):
        try:
            res = requests.get(url, timeout=15)
            data = res.json().get("VwsmAdstrdSelngW", {})
            rows = data.get("row", [])
            if isinstance(rows, dict):
                rows = [rows]
            return rows
        except Exception as e:
            print(f"  ⚠️  오류 (시도 {attempt+1}/{retries}): {e}")
            time.sleep(2)
    return []


def collect(year: int, quarter: int = None):
    """
    year: 수집 연도 (ex. 2025)
    quarter: 특정 분기만 수집 (1~4), None이면 전체
    """
    # 수집 대상 분기 목록
    if quarter:
        targets = {f"{year}{quarter}"}
        suffix = f"_{year}Q{quarter}"
    else:
        targets = {f"{year}{q}" for q in range(1, 5)}
        suffix = f"_{year}"

    output_file = os.path.join(OUTPUT_DIR, f"sangkwon{suffix}_utf8.csv")
    print(f"수집 대상: {targets}")
    print(f"저장 경로: {output_file}")

    # 전체 건수 확인
    res = requests.get(f"{BASE_URL}/1/1/", timeout=10)
    total = res.json().get("VwsmAdstrdSelngW", {}).get("list_total_count", 0)
    print(f"전체 API 데이터: {total:,}건\n{'-'*50}")

    saved = 0

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)

        # ── 전체 순회 (처음부터 끝까지) ──────────────────────
        # 기존 방식(뒤에서부터)은 4분기 누락 위험 → 전체 순회로 변경
        start = 1
        while start <= total:
            end = min(start + PAGE_SIZE - 1, total)
            print(f"  조회: {start:,}~{end:,} / {total:,} ... ", end="", flush=True)

            rows = fetch_page(start, end)
            page_saved = 0

            for r in rows:
                q = str(r.get("STDR_YYQU_CD", ""))
                if q in targets:
                    writer.writerow([r.get(c, "") for c in API_COLS])
                    saved += 1
                    page_saved += 1

            f.flush()
            print(f"{page_saved}건 저장 (누적: {saved:,})")
            start += PAGE_SIZE
            time.sleep(0.2)

    print(f"\n{'='*50}")
    print(f"✅ 완료: {saved:,}건 저장")
    print(f"파일: {output_file}")
    print(f"{'='*50}")


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    quarter = int(sys.argv[2]) if len(sys.argv) > 2 else None
    collect(year, quarter)
