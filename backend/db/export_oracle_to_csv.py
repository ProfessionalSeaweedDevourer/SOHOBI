"""
export_oracle_to_csv.py
Oracle SANGKWON_SALES / SANGKWON_STORE 테이블을 CSV로 내보내기.
PostgreSQL 이전(Step 3) 전용 1회성 스크립트.

사용법:
    cd backend
    source .env   # ORACLE_USER, ORACLE_PASSWORD, ORACLE_HOST, ORACLE_PORT, ORACLE_SID 필요
    .venv/bin/python3 db/export_oracle_to_csv.py

출력 파일:
    backend/db/sangkwon_sales.csv
    backend/db/sangkwon_store.csv
"""

import csv
import os
import sys

import oracledb
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "ORACLE_USER",
    "ORACLE_PASSWORD",
    "ORACLE_HOST",
    "ORACLE_PORT",
    "ORACLE_SID",
]
for var in REQUIRED_VARS:
    if not os.getenv(var):
        print(f"[ERROR] 환경변수 {var} 가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

EXPORTS = [
    {
        "table": "SANGKWON_SALES",
        "sql": """
            SELECT BASE_YR_QTR_CD, ADM_CD, ADM_NM, SVC_INDUTY_CD, SVC_INDUTY_NM,
                   TOT_SALES_AMT, TOT_SELNG_CO,
                   MDWK_SALES_AMT, WKEND_SALES_AMT,
                   MON_SALES_AMT, TUE_SALES_AMT, WED_SALES_AMT,
                   THU_SALES_AMT, FRI_SALES_AMT, SAT_SALES_AMT, SUN_SALES_AMT,
                   TM00_06_SALES_AMT, TM06_11_SALES_AMT, TM11_14_SALES_AMT,
                   TM14_17_SALES_AMT, TM17_21_SALES_AMT, TM21_24_SALES_AMT,
                   ML_SALES_AMT, FML_SALES_AMT,
                   AGE10_AMT, AGE20_AMT, AGE30_AMT,
                   AGE40_AMT, AGE50_AMT, AGE60_AMT
            FROM SANGKWON_SALES
        """,
        "out": os.path.join(OUT_DIR, "sangkwon_sales.csv"),
    },
    {
        "table": "SANGKWON_STORE",
        "sql": """
            SELECT BASE_YR_QTR_CD, ADM_CD, ADM_NM, SVC_INDUTY_CD, SVC_INDUTY_NM,
                   STOR_CO, SIMILR_INDUTY_STOR_CO,
                   OPBIZ_RT, OPBIZ_STOR_CO,
                   CLSBIZ_RT, CLSBIZ_STOR_CO,
                   FRC_STOR_CO
            FROM SANGKWON_STORE
        """,
        "out": os.path.join(OUT_DIR, "sangkwon_store.csv"),
    },
]


def main():
    conn = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        host=os.getenv("ORACLE_HOST"),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        sid=os.getenv("ORACLE_SID"),
    )

    for export in EXPORTS:
        print(f"[{export['table']}] 조회 중...")
        cursor = conn.cursor()
        cursor.execute(export["sql"])
        headers = [d[0].lower() for d in cursor.description]

        with open(export["out"], "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            rows = cursor.fetchall()
            writer.writerows(rows)

        print(f"[{export['table']}] {len(rows):,}행 → {export['out']}")
        cursor.close()

    conn.close()
    print("\n완료. 다음 명령으로 PostgreSQL에 적재하세요:")
    print(
        '  psql "$PG_DSN" -c "\\COPY sangkwon_sales FROM \'db/sangkwon_sales.csv\' CSV HEADER"'
    )
    print(
        '  psql "$PG_DSN" -c "\\COPY sangkwon_store FROM \'db/sangkwon_store.csv\' CSV HEADER"'
    )


if __name__ == "__main__":
    main()
