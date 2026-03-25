# =====================================================
# law_adm_map_new.csv → Oracle LAW_ADM_MAP INSERT
# 실행: python insert_law_adm.py
#
# 입력: csv/mapping/law_adm_map_new.csv
# CSV 컬럼: EMD_CD, LAW_CD, GU_NM, LAW_NM, ADM_CD, ADM_NM, CONFIDENCE
# =====================================================

import os
import csv
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "csv", "mapping", "law_adm_map_new.csv")

SQL_MERGE = """
    MERGE INTO LAW_ADM_MAP t
    USING (SELECT :1 AS EMD_CD, :2 AS LAW_CD, :3 AS GU_NM,
                  :4 AS LAW_NM, :5 AS ADM_CD, :6 AS ADM_NM,
                  :7 AS CONFIDENCE FROM DUAL) s
    ON (t.LAW_CD = s.LAW_CD)
    WHEN MATCHED THEN UPDATE SET
        t.EMD_CD=s.EMD_CD, t.GU_NM=s.GU_NM, t.LAW_NM=s.LAW_NM,
        t.ADM_CD=s.ADM_CD, t.ADM_NM=s.ADM_NM, t.CONFIDENCE=s.CONFIDENCE
    WHEN NOT MATCHED THEN INSERT
        (EMD_CD, LAW_CD, GU_NM, LAW_NM, ADM_CD, ADM_NM, CONFIDENCE)
    VALUES
        (s.EMD_CD, s.LAW_CD, s.GU_NM, s.LAW_NM, s.ADM_CD, s.ADM_NM, s.CONFIDENCE)
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

            emd_cd = keys.get("EMD_CD", "")
            law_cd = keys.get("LAW_CD", "")
            gu_nm = keys.get("GU_NM", "")
            law_nm = keys.get("LAW_NM", "")
            adm_cd = keys.get("ADM_CD", "")
            adm_nm = keys.get("ADM_NM", "")
            confidence = keys.get("CONFIDENCE", "")

            if not law_cd:
                continue

            rows.append(
                (
                    emd_cd or None,
                    law_cd,
                    gu_nm or None,
                    law_nm or None,
                    adm_cd or None,
                    adm_nm or None,
                    confidence or None,
                )
            )

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
                logger.error(f"  스킵: {r[1]} / {e2}")
        con.commit()
        logger.info(f"개별 INSERT: {ok}/{len(rows)}건")
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    main()
