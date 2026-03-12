# collect_2025_raw.py
# 2025년 상권분석 매출 raw 데이터 수집 (업종별 그대로)
# 실행: python collect_2025_raw.py
# 결과: march03_1_backend\csvCollector\sangkwon_2025_raw.csv

import requests
import csv
import time
import os

SANGKWON_KEY = "754877586377737436326350494f4c"
BASE_URL = f"http://openapi.seoul.go.kr:8088/{SANGKWON_KEY}/json/VwsmAdstrdSelngW"
PAGE_SIZE = 1000

OUTPUT_DIR = r"C:\Users\user\Desktop\SW2_TERRY\project\march03_1_backend\csvCollector"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sangkwon_2025_raw.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


def main():
    # 1) 전체 건수 확인
    print("전체 데이터 건수 확인 중...")
    res = requests.get(f"{BASE_URL}/1/1/", timeout=10)
    total = res.json().get("VwsmAdstrdSelngW", {}).get("list_total_count", 0)
    print(f"전체 데이터: {total:,}건")
    print(f"저장 경로: {OUTPUT_FILE}")
    print("-" * 50)

    saved = 0

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)

        # 2) 뒤에서부터 수집 (최신 데이터가 뒤에 있음)
        start = total
        while start > 0:
            s = max(1, start - PAGE_SIZE + 1)
            url = f"{BASE_URL}/{s}/{start}/"
            print(f"  조회: {s}~{start} ... ", end="", flush=True)

            try:
                res = requests.get(url, timeout=15)
                rows = res.json().get("VwsmAdstrdSelngW", {}).get("row", [])
                if isinstance(rows, dict):
                    rows = [rows]
            except Exception as e:
                print(f"오류: {e}, 재시도...")
                time.sleep(2)
                continue

            page_saved = 0
            stop = False
            for r in rows:
                q = r.get("STDR_YYQU_CD", "")
                if q.startswith("2025"):
                    writer.writerow([r.get(c, "") for c in API_COLS])
                    saved += 1
                    page_saved += 1
                elif q and int(q[:4]) < 2025:
                    stop = True
                    break

            f.flush()  # 페이지마다 파일에 즉시 쓰기
            print(f"{page_saved}건 저장 (누적: {saved:,})")

            if stop:
                print("2024년 이하 데이터 도달 → 수집 완료!")
                break

            start = s - 1
            time.sleep(0.3)

    print("\n" + "=" * 50)
    print(f"완료! 총 {saved:,}건 저장")
    print(f"파일: {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
