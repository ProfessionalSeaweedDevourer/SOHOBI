# =====================================================
# svc_induty_map.csv → Oracle SVC_INDUTY_MAP INSERT
# 실행: python insert_svc_induty_map.py
#
# 입력: csv/mapping/svc_induty_map.csv
# CSV 컬럼: SVC_INDUTY_CD, SVC_INDUTY_NM, SVC_CD, SVC_NM
# =====================================================

import os
import csv
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_INFO  = "shobi/8680@//10.1.92.119:1521/xe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "csv", "mapping", "svc_induty_map.csv")

SQL_MERGE = """
    MERGE INTO SVC_INDUTY_MAP t
    USING (SELECT :1 AS SVC_INDUTY_CD, :2 AS SVC_INDUTY_NM,
                  :3 AS SVC_CD, :4 AS SVC_NM FROM DUAL) s
    ON (t.SVC_INDUTY_CD = s.SVC_INDUTY_CD)
    WHEN MATCHED THEN UPDATE SET
        t.SVC_INDUTY_NM=s.SVC_INDUTY_NM,
        t.SVC_CD=s.SVC_CD,
        t.SVC_NM=s.SVC_NM
    WHEN NOT MATCHED THEN INSERT
        (SVC_INDUTY_CD, SVC_INDUTY_NM, SVC_CD, SVC_NM)
    VALUES
        (s.SVC_INDUTY_CD, s.SVC_INDUTY_NM, s.SVC_CD, s.SVC_NM)
"""

def main():
    if not os.path.exists(CSV_PATH):
        logger.error(f"파일 없음: {CSV_PATH}")
        return

    logger.info(f"파일: {CSV_PATH}")

    encoding = "utf-8-sig"
    try:
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            f.read(1024)
    except UnicodeDecodeError:
        encoding = "cp949"
    logger.info(f"인코딩: {encoding}")

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    rows = []
    with open(CSV_PATH, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        logger.info(f"컬럼: {reader.fieldnames}")
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            keys = {k.upper(): v for k, v in row.items()}
            svc_induty_cd = keys.get("SVC_INDUTY_CD", "")
            if not svc_induty_cd:
                continue
            rows.append((
                svc_induty_cd,
                keys.get("SVC_INDUTY_NM", "") or None,
                keys.get("SVC_CD", "")        or None,
                keys.get("SVC_NM", "")        or None,
            ))

    logger.info(f"총 {len(rows)}건 로드")

    try:
        cur.executemany(SQL_MERGE, rows)
        con.commit()
        logger.info(f"✅ {len(rows)}건 INSERT/UPDATE 완료")
    except Exception as e:
        con.rollback()
        logger.error(f"오류: {e}")
        ok = 0
        for r in rows:
            try:
                cur.execute(SQL_MERGE, r)
                ok += 1
            except Exception as e2:
                logger.error(f"  스킵: {r[0]} / {e2}")
        con.commit()
        logger.info(f"개별 INSERT: {ok}/{len(rows)}건")
    finally:
        cur.close()
        con.close()

if __name__ == "__main__":
    main()
