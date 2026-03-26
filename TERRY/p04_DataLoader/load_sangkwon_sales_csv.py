# =====================================================
# 골목상권 매출 CSV → Oracle SANGKWON_SALES INSERT
# 실행: python load_sangkwon_sales_csv.py [폴더경로] [옵션]
#
# 사용법:
#   python load_sangkwon_sales_csv.py                          ← 전체
#   python load_sangkwon_sales_csv.py csv/sangkwon_sales       ← 폴더 지정
#   python load_sangkwon_sales_csv.py --year=2024              ← 2024년 파일만
#   python load_sangkwon_sales_csv.py --year=2024 --qtr=3      ← 2024년 3분기만
#
# CSV 컬럼 (collect_sangkwon_sales.py 수집 결과 - 영문):
#   STDR_YYQU_CD, ADSTRD_CD, ADSTRD_CD_NM, SVC_INDUTY_CD, ...
# =====================================================

import os
import sys
import glob
import csv
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
BATCH = 1000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── API 영문 컬럼 → DB 컬럼 매핑 ─────────────────────────────
COL_MAP = {
    # 영문 (collect_sangkwon_sales.py 결과)
    "STDR_YYQU_CD": "base_yr_qtr_cd",
    "ADSTRD_CD": "adm_cd",
    "ADSTRD_CD_NM": "adm_nm",
    "SVC_INDUTY_CD": "svc_induty_cd",
    "SVC_INDUTY_CD_NM": "svc_induty_nm",
    "THSMON_SELNG_AMT": "tot_sales_amt",
    "THSMON_SELNG_CO": "tot_selng_co",
    "MDWK_SELNG_AMT": "mdwk_sales_amt",
    "WKEND_SELNG_AMT": "wkend_sales_amt",
    "MON_SELNG_AMT": "mon_sales_amt",
    "TUES_SELNG_AMT": "tue_sales_amt",
    "WED_SELNG_AMT": "wed_sales_amt",
    "THUR_SELNG_AMT": "thu_sales_amt",
    "FRI_SELNG_AMT": "fri_sales_amt",
    "SAT_SELNG_AMT": "sat_sales_amt",
    "SUN_SELNG_AMT": "sun_sales_amt",
    "TM00_06_SELNG_AMT": "tm00_06_sales_amt",
    "TM06_11_SELNG_AMT": "tm06_11_sales_amt",
    "TM11_14_SELNG_AMT": "tm11_14_sales_amt",
    "TM14_17_SELNG_AMT": "tm14_17_sales_amt",
    "TM17_21_SELNG_AMT": "tm17_21_sales_amt",
    "TM21_24_SELNG_AMT": "tm21_24_sales_amt",
    "ML_SELNG_AMT": "ml_sales_amt",
    "FML_SELNG_AMT": "fml_sales_amt",
    "AGRDE_10_SELNG_AMT": "age10_amt",
    "AGRDE_20_SELNG_AMT": "age20_amt",
    "AGRDE_30_SELNG_AMT": "age30_amt",
    "AGRDE_40_SELNG_AMT": "age40_amt",
    "AGRDE_50_SELNG_AMT": "age50_amt",
    "AGRDE_60_ABOVE_SELNG_AMT": "age60_amt",
    "MDWK_SELNG_CO": "mdwk_selng_co",
    "WKEND_SELNG_CO": "wkend_selng_co",
    "MON_SELNG_CO": "mon_selng_co",
    "TUES_SELNG_CO": "tue_selng_co",
    "WED_SELNG_CO": "wed_selng_co",
    "THUR_SELNG_CO": "thu_selng_co",
    "FRI_SELNG_CO": "fri_selng_co",
    "SAT_SELNG_CO": "sat_selng_co",
    "SUN_SELNG_CO": "sun_selng_co",
    "TM00_06_SELNG_CO": "tm00_06_selng_co",
    "TM06_11_SELNG_CO": "tm06_11_selng_co",
    "TM11_14_SELNG_CO": "tm11_14_selng_co",
    "TM14_17_SELNG_CO": "tm14_17_selng_co",
    "TM17_21_SELNG_CO": "tm17_21_selng_co",
    "TM21_24_SELNG_CO": "tm21_24_selng_co",
    "ML_SELNG_CO": "ml_selng_co",
    "FML_SELNG_CO": "fml_selng_co",
    "AGRDE_10_SELNG_CO": "age10_selng_co",
    "AGRDE_20_SELNG_CO": "age20_selng_co",
    "AGRDE_30_SELNG_CO": "age30_selng_co",
    "AGRDE_40_SELNG_CO": "age40_selng_co",
    "AGRDE_50_SELNG_CO": "age50_selng_co",
    "AGRDE_60_ABOVE_SELNG_CO": "age60_selng_co",
    # 한글 컬럼 (기존 CSV 호환)
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

STR_COLS = {"base_yr_qtr_cd", "adm_cd", "adm_nm", "svc_induty_cd", "svc_induty_nm"}


def to_num(val):
    v = str(val).strip()
    if not v or v in ("-", "N/A", "null", "NULL"):
        return None
    try:
        return int(float(v))
    except:
        return None


def load_file(cur, csv_path, year_flt=None, qtr_flt=None):
    """
    year_flt: "2024" → STDR_YYQU_CD가 2024로 시작하는 행만
    qtr_flt:  "3"    → STDR_YYQU_CD가 XXXX3인 행만 (20243 등)
    둘 다 지정 시 AND 조건 (예: 2024년 3분기 = "20243")
    """
    ok = skip = filtered = 0

    # 인코딩 자동 감지
    encoding = "utf-8-sig"
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            f.read(1024)
    except UnicodeDecodeError:
        encoding = "cp949"

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        csv_cols = reader.fieldnames

        # 헤더 매핑
        db_cols = []
        for c in csv_cols:
            mapped = COL_MAP.get(c.strip())
            if mapped and mapped not in db_cols:
                db_cols.append(mapped)

        if not db_cols:
            logger.error(f"매핑된 컬럼 없음: {csv_path}")
            return 0, 0

        placeholders = ", ".join(f":{i+1}" for i in range(len(db_cols)))
        sql = (
            f"INSERT INTO SANGKWON_SALES ({', '.join(db_cols)}) VALUES ({placeholders})"
        )

        # STDR_YYQU_CD 컬럼 찾기 (영문/한글 둘 다)
        qtr_col = next(
            (c for c in csv_cols if c.strip() in ("STDR_YYQU_CD", "기준_년분기_코드")),
            None,
        )

        batch = []
        for row in reader:
            # 연도/분기 필터
            if qtr_col and (year_flt or qtr_flt):
                qtr_val = str(row.get(qtr_col, "")).strip()
                if year_flt and not qtr_val.startswith(year_flt):
                    filtered += 1
                    continue
                if qtr_flt and not qtr_val.endswith(qtr_flt):
                    filtered += 1
                    continue

            vals = []
            used = set()
            for c in csv_cols:
                db_c = COL_MAP.get(c.strip())
                if not db_c or db_c not in db_cols or db_c in used:
                    continue
                used.add(db_c)
                raw = row.get(c, "")
                vals.append(raw.strip() if db_c in STR_COLS else to_num(raw))
            batch.append(vals)

            if len(batch) >= BATCH:
                try:
                    cur.executemany(sql, batch)
                    ok += len(batch)
                except Exception as e:
                    for rv in batch:
                        try:
                            cur.execute(sql, rv)
                            ok += 1
                        except:
                            skip += 1
                batch = []

        if batch:
            try:
                cur.executemany(sql, batch)
                ok += len(batch)
            except:
                for rv in batch:
                    try:
                        cur.execute(sql, rv)
                        ok += 1
                    except:
                        skip += 1

    if filtered:
        logger.info(f"  필터 스킵: {filtered:,}건 (year={year_flt} qtr={qtr_flt})")
    return ok, skip


def main():
    # ── 인자 파싱 ─────────────────────────────────────────────
    csv_dir = None
    year_flt = None
    qtr_flt = None

    for a in sys.argv[1:]:
        if a.startswith("--year="):
            year_flt = a.split("=")[1]
        elif a.startswith("--qtr="):
            qtr_flt = a.split("=")[1]
        elif not a.startswith("--"):
            csv_dir = a

    if not csv_dir:
        csv_dir = os.path.join(BASE_DIR, "csv", "sangkwon_sales")

    logger.info(f"CSV 폴더: {csv_dir}")
    if year_flt:
        logger.info(f"연도 필터: {year_flt}년")
    if qtr_flt:
        logger.info(f"분기 필터: {qtr_flt}분기")

    # 파일 탐색
    all_files = sorted(
        glob.glob(os.path.join(csv_dir, "**", "*.csv"), recursive=True)
        or glob.glob(os.path.join(csv_dir, "*.csv"))
    )

    # 연도/분기 필터 (파일명 기준)
    csv_files = []
    for f in all_files:
        fname = os.path.basename(f)
        if year_flt and year_flt not in fname:
            continue
        csv_files.append(f)

    if not csv_files:
        logger.error(f"CSV 파일 없음 (필터: year={year_flt} qtr={qtr_flt})")
        return

    logger.info(f"총 {len(csv_files)}개 파일")

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    total_ok = total_skip = 0
    for i, path in enumerate(csv_files, 1):
        fname = os.path.basename(path)
        logger.info(f"[{i}/{len(csv_files)}] {fname}")
        ok, skip = load_file(cur, path, year_flt=year_flt, qtr_flt=qtr_flt)
        con.commit()
        total_ok += ok
        total_skip += skip
        logger.info(f"  ✅ {ok:,}건 INSERT / {skip:,}건 스킵")

    cur.close()
    con.close()
    logger.info(f"{'='*40}")
    logger.info(f"완료: {total_ok:,}건 INSERT / {total_skip:,}건 스킵")


if __name__ == "__main__":
    main()
