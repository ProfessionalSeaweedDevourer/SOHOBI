# =====================================================
# 골목상권 CSV → Oracle SANGKWON_SALES 자동 적재
# 실행: python load_sangkwon_csv.py
# CSV 폴더 안의 모든 .csv 파일을 순서대로 INSERT
# =====================================================

import os
import glob
import csv
import oracledb
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
# ── CSV 폴더 경로 ──────────────────────────────────
# 연도별 폴더 지정: csv/sangkwon_sales/sangkwon_2024_utf8 등
import sys

CSV_DIR = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "csv", "sangkwon_sales"
    )
)
ENCODING = "utf-8-sig"  # BOM 있는 경우 자동 처리
BATCH = 1000  # 한 번에 INSERT할 행 수
# ──────────────────────────────────────────────────

# CSV 헤더 → DB 컬럼명 매핑 (53개)
COL_MAP = {
    "기준_년분기_코드": "base_yr_qtr_cd",
    "행정동_코드": "adm_cd",
    "행정동_코드_명": "adm_nm",
    "서비스_업종_코드": "svc_induty_cd",
    "서비스_업종_코드_명": "svc_induty_nm",
    "당월_매출_금액": "tot_sales_amt",
    "당월_매출_건수": "tot_selng_co",
    "주중_매출_금액": "mdwk_sales_amt",
    "주말_매출_금액": "wkend_sales_amt",
    "월요일_매출_금액": "mon_sales_amt",
    "화요일_매출_금액": "tue_sales_amt",
    "수요일_매출_금액": "wed_sales_amt",
    "목요일_매출_금액": "thu_sales_amt",
    "금요일_매출_금액": "fri_sales_amt",
    "토요일_매출_금액": "sat_sales_amt",
    "일요일_매출_금액": "sun_sales_amt",
    "시간대_00~06_매출_금액": "tm00_06_sales_amt",
    "시간대_06~11_매출_금액": "tm06_11_sales_amt",
    "시간대_11~14_매출_금액": "tm11_14_sales_amt",
    "시간대_14~17_매출_금액": "tm14_17_sales_amt",
    "시간대_17~21_매출_금액": "tm17_21_sales_amt",
    "시간대_21~24_매출_금액": "tm21_24_sales_amt",
    "남성_매출_금액": "ml_sales_amt",
    "여성_매출_금액": "fml_sales_amt",
    "연령대_10_매출_금액": "age10_amt",
    "연령대_20_매출_금액": "age20_amt",
    "연령대_30_매출_금액": "age30_amt",
    "연령대_40_매출_금액": "age40_amt",
    "연령대_50_매출_금액": "age50_amt",
    "연령대_60_이상_매출_금액": "age60_amt",
    "주중_매출_건수": "mdwk_selng_co",
    "주말_매출_건수": "wkend_selng_co",
    "월요일_매출_건수": "mon_selng_co",
    "화요일_매출_건수": "tue_selng_co",
    "수요일_매출_건수": "wed_selng_co",
    "목요일_매출_건수": "thu_selng_co",
    "금요일_매출_건수": "fri_selng_co",
    "토요일_매출_건수": "sat_selng_co",
    "일요일_매출_건수": "sun_selng_co",
    "시간대_건수~06_매출_건수": "tm00_06_selng_co",
    "시간대_건수~11_매출_건수": "tm06_11_selng_co",
    "시간대_건수~14_매출_건수": "tm11_14_selng_co",
    "시간대_건수~17_매출_건수": "tm14_17_selng_co",
    "시간대_건수~21_매출_건수": "tm17_21_selng_co",
    "시간대_건수~24_매출_건수": "tm21_24_selng_co",
    "남성_매출_건수": "ml_selng_co",
    "여성_매출_건수": "fml_selng_co",
    "연령대_10_매출_건수": "age10_selng_co",
    "연령대_20_매출_건수": "age20_selng_co",
    "연령대_30_매출_건수": "age30_selng_co",
    "연령대_40_매출_건수": "age40_selng_co",
    "연령대_50_매출_건수": "age50_selng_co",
    "연령대_60_이상_매출_건수": "age60_selng_co",
}


def to_num(val):
    """빈값/공백 → None, 숫자 문자열 → int"""
    v = str(val).strip()
    if not v or v in ("-", "N/A", "null", "NULL"):
        return None
    try:
        return int(float(v))
    except:
        return None


def load_csv(cur, csv_path: str) -> tuple[int, int]:
    """CSV 한 파일 → DB INSERT, (성공건, 스킵건) 반환"""
    ok = skip = 0

    with open(csv_path, encoding=ENCODING, newline="") as f:
        reader = csv.DictReader(f)

        # CSV 헤더 → DB 컬럼 매핑
        csv_cols = reader.fieldnames
        db_cols = []
        for c in csv_cols:
            mapped = COL_MAP.get(c.strip())
            if mapped:
                db_cols.append(mapped)
            else:
                print(f"  ⚠️  매핑 없는 컬럼 무시: '{c}'")

        if not db_cols:
            print(f"  ❌ 매핑된 컬럼 없음, 스킵")
            return 0, 0

        # VARCHAR 컬럼 (문자열 그대로), 나머지는 숫자 변환
        STR_COLS = {
            "base_yr_qtr_cd",
            "adm_cd",
            "adm_nm",
            "svc_induty_cd",
            "svc_induty_nm",
        }

        placeholders = ", ".join(f":{i+1}" for i in range(len(db_cols)))
        sql = (
            f"INSERT INTO SANGKWON_SALES ({', '.join(db_cols)}) VALUES ({placeholders})"
        )

        batch = []
        for row in reader:
            vals = []
            for csv_c, db_c in zip(csv_cols, db_cols):
                raw = row.get(csv_c, "")
                vals.append(raw.strip() if db_c in STR_COLS else to_num(raw))
            batch.append(vals)

            if len(batch) >= BATCH:
                try:
                    cur.executemany(sql, batch)
                    ok += len(batch)
                except Exception as e:
                    print(f"  ⚠️  batch 오류 (개별 INSERT 시도): {e}")
                    for row_vals in batch:
                        try:
                            cur.execute(sql, row_vals)
                            ok += 1
                        except Exception as e2:
                            skip += 1
                batch = []

        # 나머지
        if batch:
            try:
                cur.executemany(sql, batch)
                ok += len(batch)
            except Exception as e:
                for row_vals in batch:
                    try:
                        cur.execute(sql, row_vals)
                        ok += 1
                    except:
                        skip += 1

    return ok, skip


def main():
    print(f"CSV 폴더: {CSV_DIR}")
    # 하위 폴더까지 재귀 탐색
    csv_files = sorted(
        glob.glob(os.path.join(CSV_DIR, "**", "*.csv"), recursive=True)
        or glob.glob(os.path.join(CSV_DIR, "*.csv"))
    )
    if not csv_files:
        print(f"❌ CSV 파일 없음: {CSV_DIR}")
        print(f"사용법: python load_sangkwon_sales_csv.py [폴더경로]")
        print(
            f"  예시: python load_sangkwon_sales_csv.py csv/sangkwon_sales/sangkwon_2024_utf8"
        )
        return

    print(f"총 {len(csv_files)}개 CSV 파일 발견")
    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    total_ok = total_skip = 0
    for i, path in enumerate(csv_files, 1):
        fname = os.path.basename(path)
        print(f"\n[{i}/{len(csv_files)}] {fname} ...")
        ok, skip = load_csv(cur, path)
        con.commit()
        total_ok += ok
        total_skip += skip
        print(f"  ✅ {ok:,}건 INSERT  |  ⚠️ {skip:,}건 스킵")

    cur.close()
    con.close()
    print(f"\n{'='*40}")
    print(f"완료: 총 {total_ok:,}건 INSERT  |  {total_skip:,}건 스킵")


if __name__ == "__main__":
    main()
