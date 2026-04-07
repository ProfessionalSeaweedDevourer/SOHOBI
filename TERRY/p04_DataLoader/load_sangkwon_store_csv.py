# =====================================================
# 골목상권 점포수 CSV → Oracle SANGKWON_STORE INSERT
# 실행: python load_sangkwon_store_csv.py [폴더경로]
#
# CSV 컬럼:
#   STDR_YYQU_CD       → BASE_YR_QTR_CD  기준년분기코드
#   ADSTRD_CD          → ADM_CD          행정동코드
#   ADSTRD_CD_NM       → ADM_NM          행정동명
#   SVC_INDUTY_CD      → SVC_INDUTY_CD   서비스업종코드
#   SVC_INDUTY_CD_NM   → SVC_INDUTY_NM   서비스업종명
#   STOR_CO            → STOR_CO         점포수
#   SIMILR_INDUTY_STOR_CO → SIMILR_INDUTY_STOR_CO 유사업종수
#   OPBIZ_RT           → OPBIZ_RT        개업률
#   OPBIZ_STOR_CO      → OPBIZ_STOR_CO   개업수
#   CLSBIZ_RT          → CLSBIZ_RT       폐업률
#   CLSBIZ_STOR_CO     → CLSBIZ_STOR_CO  폐업수
#   FRC_STOR_CO        → FRC_STOR_CO     프랜차이즈수
# =====================================================


import os
import sys
import csv
import glob
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
BATCH_SIZE = 1000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# CSV 헤더 → DB 컬럼 매핑
COL_MAP = {
    "STDR_YYQU_CD": "BASE_YR_QTR_CD",
    "ADSTRD_CD": "ADM_CD",
    "ADSTRD_CD_NM": "ADM_NM",
    "SVC_INDUTY_CD": "SVC_INDUTY_CD",
    "SVC_INDUTY_CD_NM": "SVC_INDUTY_NM",
    "STOR_CO": "STOR_CO",
    "SIMILR_INDUTY_STOR_CO": "SIMILR_INDUTY_STOR_CO",
    "OPBIZ_RT": "OPBIZ_RT",
    "OPBIZ_STOR_CO": "OPBIZ_STOR_CO",
    "CLSBIZ_RT": "CLSBIZ_RT",
    "CLSBIZ_STOR_CO": "CLSBIZ_STOR_CO",
    "FRC_STOR_CO": "FRC_STOR_CO",
}

DB_COLS = list(COL_MAP.values())
STR_COLS = {"BASE_YR_QTR_CD", "ADM_CD", "ADM_NM", "SVC_INDUTY_CD", "SVC_INDUTY_NM"}

SQL_INSERT = f"""
    INSERT INTO SANGKWON_STORE ({', '.join(DB_COLS)})
    VALUES ({', '.join([f':{i+1}' for i in range(len(DB_COLS))])})
"""


def to_num(val):
    v = str(val).strip()
    if not v or v in ("-", "N/A", "null", "NULL"):
        return None
    try:
        return float(v)
    except:
        return None


def parse_row(row, col_idx):
    vals = []
    for csv_col, db_col in COL_MAP.items():
        idx = col_idx.get(csv_col)
        raw = row[idx].strip() if idx is not None and idx < len(row) else ""
        if db_col in STR_COLS:
            vals.append(raw if raw else None)
        else:
            vals.append(to_num(raw))
    return tuple(vals)


def load_csv(csv_path, con, cur, year_flt=None, qtr_flt=None):
    fname = os.path.basename(csv_path)
    logger.info(f"처리 중: {fname}")

    # 인코딩 자동 감지
    encoding = "utf-8-sig"
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            f.read(1024)
    except UnicodeDecodeError:
        encoding = "cp949"

    ok = skip = filtered = 0
    batch = []

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)
        col_idx = {h.strip(): i for i, h in enumerate(headers)}

        # STDR_YYQU_CD 컬럼 인덱스
        qtr_idx = col_idx.get("STDR_YYQU_CD")

        # 컬럼 검증
        missing = [k for k in COL_MAP if k not in col_idx]
        if missing:
            logger.warning(f"누락 컬럼: {missing}")

        for row in reader:
            # 연도/분기 필터 (행 레벨)
            if qtr_idx is not None and (year_flt or qtr_flt):
                qtr_val = row[qtr_idx].strip() if qtr_idx < len(row) else ""
                if year_flt and not qtr_val.startswith(year_flt):
                    filtered += 1
                    continue
                if qtr_flt and not qtr_val.endswith(qtr_flt):
                    filtered += 1
                    continue

            batch.append(parse_row(row, col_idx))

            if len(batch) >= BATCH_SIZE:
                try:
                    cur.executemany(SQL_INSERT, batch)
                    con.commit()
                    ok += len(batch)
                except Exception as e:
                    if "ORA-00001" in str(e):
                        con.rollback()
                        for r in batch:
                            try:
                                cur.execute(SQL_INSERT, r)
                                con.commit()
                                ok += 1
                            except:
                                con.rollback()
                                skip += 1
                    else:
                        logger.error(f"배치 오류: {e}")
                        con.rollback()
                        skip += len(batch)
                batch = []

    # 나머지
    if batch:
        try:
            cur.executemany(SQL_INSERT, batch)
            con.commit()
            ok += len(batch)
        except Exception as e:
            con.rollback()
            for r in batch:
                try:
                    cur.execute(SQL_INSERT, r)
                    con.commit()
                    ok += 1
                except:
                    con.rollback()
                    skip += 1

    if filtered:
        logger.info(f"  필터 스킵: {filtered:,}건 (year={year_flt} qtr={qtr_flt})")
    logger.info(f"  ✅ {ok:,}건 INSERT / {skip:,}건 스킵")
    return ok, skip


def main():
    # ── 인자 파싱 ─────────────────────────────────────────────
    # 사용법:
    #   python load_sangkwon_store_csv.py                     ← 전체
    #   python load_sangkwon_store_csv.py --year=2024         ← 2024년 파일만
    #   python load_sangkwon_store_csv.py --year=2024 --qtr=3 ← 2024년 3분기만
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
        csv_dir = os.path.join(BASE_DIR, "csv", "sangkwon_store")

    logger.info(f"CSV 폴더: {csv_dir}")
    if year_flt:
        logger.info(f"연도 필터: {year_flt}년")
    if qtr_flt:
        logger.info(f"분기 필터: {qtr_flt}분기")

    all_files = sorted(
        glob.glob(os.path.join(csv_dir, "**", "*.csv"), recursive=True)
        or glob.glob(os.path.join(csv_dir, "*.csv"))
    )

    csv_files = []
    for f in all_files:
        fname = os.path.basename(f)
        if year_flt and year_flt not in fname:
            continue
        if qtr_flt and qtr_flt not in fname:
            continue
        csv_files.append(f)

    if not csv_files:
        logger.error(f"CSV 파일 없음 (필터: year={year_flt} qtr={qtr_flt})")
        logger.info("사용법: python load_sangkwon_store_csv.py [--year=2024] [--qtr=3]")
        return

    logger.info(f"총 {len(csv_files)}개 파일 발견")

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    total_ok = total_skip = 0
    for i, path in enumerate(csv_files, 1):
        logger.info(f"[{i}/{len(csv_files)}] {os.path.basename(path)}")
        ok, skip = load_csv(path, con, cur, year_flt=year_flt, qtr_flt=qtr_flt)
        total_ok += ok
        total_skip += skip

    cur.close()
    con.close()
    logger.info(f"\n{'='*40}")
    logger.info(f"완료: 총 {total_ok:,}건 INSERT / {total_skip:,}건 스킵")


if __name__ == "__main__":
    main()
