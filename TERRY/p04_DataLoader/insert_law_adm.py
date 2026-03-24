# =====================================================
# law_adm_map_new.csv → Oracle LAW_ADM_MAP INSERT
# 실행: python insert_law_adm.py
#
# 입력: csv/mapping/law_adm_map_new.csv
# 대상: LAW_ADM_MAP 테이블
#
# 테이블 구조 (MS2_PROJECT_Create_dong.sql):
#   LAW_CD    VARCHAR2(10) - 법정동코드
#   LAW_NM    VARCHAR2(100)- 법정동명
#   ADM_CD    VARCHAR2(10) - 행정동코드
#   ADM_NM    VARCHAR2(100)- 행정동명
#   GU_NM     VARCHAR2(50) - 구이름
# =====================================================

import os
import csv
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "csv", "mapping", "law_adm_map_new.csv")

SQL_MERGE = """
    MERGE INTO LAW_ADM_MAP t
    USING (SELECT :1 AS LAW_CD, :2 AS LAW_NM, :3 AS ADM_CD,
                  :4 AS ADM_NM, :5 AS GU_NM FROM DUAL) s
    ON (t.LAW_CD = s.LAW_CD)
    WHEN MATCHED THEN UPDATE SET
        t.LAW_NM=s.LAW_NM, t.ADM_CD=s.ADM_CD,
        t.ADM_NM=s.ADM_NM, t.GU_NM=s.GU_NM
    WHEN NOT MATCHED THEN INSERT
        (LAW_CD, LAW_NM, ADM_CD, ADM_NM, GU_NM)
    VALUES
        (s.LAW_CD, s.LAW_NM, s.ADM_CD, s.ADM_NM, s.GU_NM)
"""


def main():
    if not os.path.exists(CSV_PATH):
        logger.error(f"파일 없음: {CSV_PATH}")
        return

    logger.info(f"파일: {CSV_PATH}")

    # 인코딩 자동 감지
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
            # 컬럼명 공백 제거
            row = {k.strip(): v.strip() for k, v in row.items()}

            # 컬럼명 자동 매핑 (대소문자 무관)
            keys = {k.upper(): v for k, v in row.items()}
            law_cd = keys.get("LAW_CD") or keys.get("법정동코드") or ""
            law_nm = keys.get("LAW_NM") or keys.get("법정동명") or ""
            adm_cd = keys.get("ADM_CD") or keys.get("행정동코드") or ""
            adm_nm = keys.get("ADM_NM") or keys.get("행정동명") or ""
            gu_nm = keys.get("GU_NM") or keys.get("구이름") or ""

            if not law_cd:
                continue
            rows.append((law_cd, law_nm, adm_cd or None, adm_nm or None, gu_nm or None))

    logger.info(f"총 {len(rows)}건 로드")

    try:
        cur.executemany(SQL_MERGE, rows)
        con.commit()
        logger.info(f"✅ {len(rows)}건 INSERT/UPDATE 완료")
    except Exception as e:
        con.rollback()
        logger.error(f"오류: {e}")
        # 개별 INSERT 시도
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
