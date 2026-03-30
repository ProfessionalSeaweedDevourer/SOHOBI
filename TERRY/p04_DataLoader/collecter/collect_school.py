# =====================================================
# 서울시 학교 정보 수집 → Oracle INSERT
# 위치: p04_DataLoader/collector/collect_school.py
#
# API: 서울 열린데이터광장 학교 정보
# END_POINT: http://openapi.seoul.go.kr:8088/(키)/xml/neisSchoolInfo/1/5/
#
# 사용법:
#   python collect_school.py              ← 전체 수집
#   python collect_school.py --type=초등학교 ← 특정 학교종류만
# =====================================================

import os
import sys
import asyncio
import logging
import xml.etree.ElementTree as ET

import httpx
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_INFO      = "shobi/8680@//10.1.92.119:1521/xe"
SEOUL_KEY    = os.getenv("SEOUL_SCHOOL_API_KEY", "6e626d744d777374373748684e7575")
BASE_URL     = f"http://openapi.seoul.go.kr:8088/{SEOUL_KEY}/xml/neisSchoolInfo"
PAGE_SIZE    = 1000

# INSERT + ORA-00001(PK중복) 무시 방식 (MERGE는 oracledb 바인드 카운트 버그)
SQL_INSERT = """
    INSERT INTO SCHOOL_SEOUL (
        SCHOOL_ID, SCHOOL_NM, ENG_SCHOOL_NM, SCHOOL_TYPE,
        SIDO_NM, ORG_NM, FOUND_TYPE, ZIPCODE,
        ROAD_ADDR, ROAD_ADDR2, TEL, FAX, HOMEPAGE,
        COEDU_TYPE, FOUND_DATE, OPEN_DATE, DAY_NIGHT
    ) VALUES (
        :1, :2, :3, :4, :5, :6, :7, :8,
        :9, :10, :11, :12, :13, :14, :15, :16, :17
    )
"""

def g(item, tag):
    return (item.findtext(tag) or '').strip()

def to_float(val):
    try: return float(val.strip()) if val and val.strip() else None
    except: return None


async def fetch_page(client, start, end):
    try:
        url = f"{BASE_URL}/{start}/{end}/"
        r = await client.get(url, timeout=20)
        root  = ET.fromstring(r.text)
        total = int(root.findtext('.//list_total_count') or 0)
        rows  = root.findall('.//row')
        return total, rows
    except Exception as e:
        logger.error(f"fetch_page 오류: {e}")
        return 0, []


async def main():
    type_filter = None
    for a in sys.argv[1:]:
        if a.startswith("--type="):
            type_filter = a.split("=")[1]

    logger.info(f"학교 수집 시작 (필터: {type_filter or '전체'})")

    async with httpx.AsyncClient() as client:
        # 전체 건수 확인
        total, _ = await fetch_page(client, 1, 1)
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        logger.info(f"전체: {total}건 / {total_pages}페이지")

        all_rows = []
        for page in range(total_pages):
            start = page * PAGE_SIZE + 1
            end   = (page + 1) * PAGE_SIZE
            _, rows = await fetch_page(client, start, end)
            all_rows.extend(rows)
            logger.info(f"  페이지 {page+1}/{total_pages}: {len(rows)}건")
            await asyncio.sleep(0.2)

    # 파싱
    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    rows_data = []
    skip_type = 0
    for row in all_rows:
        school_type = g(row, 'SCHUL_KND_SC_NM')

        # 학교종류 필터 (--type 옵션 사용 시)
        if type_filter and type_filter not in school_type:
            skip_type += 1
            continue

        rows_data.append((
            g(row, 'SD_SCHUL_CODE'),       # SCHOOL_ID
            g(row, 'SCHUL_NM'),            # SCHOOL_NM
            g(row, 'ENG_SCHUL_NM') or None,# ENG_SCHOOL_NM
            school_type,                    # SCHOOL_TYPE
            g(row, 'LCTN_SC_NM'),          # SIDO_NM
            g(row, 'JU_ORG_NM') or None,   # ORG_NM (교육지원청)
            g(row, 'FOND_SC_NM') or None,  # FOUND_TYPE (공립/사립)
            g(row, 'ORG_RDNZC') or None,   # ZIPCODE
            g(row, 'ORG_RDNMA') or None,   # ROAD_ADDR
            g(row, 'ORG_RDNDA') or None,   # ROAD_ADDR2
            g(row, 'ORG_TELNO') or None,   # TEL
            g(row, 'ORG_FAXNO') or None,   # FAX
            g(row, 'HMPG_ADRES') or None,  # HOMEPAGE
            g(row, 'COEDU_SC_NM') or None, # COEDU_TYPE
            g(row, 'FOND_YMD') or None,    # FOUND_DATE
            g(row, 'FOAS_MEMRD') or None,  # OPEN_DATE
            g(row, 'DGHT_SC_NM') or None,  # DAY_NIGHT
        ))

    logger.info(f"적재 대상: {len(rows_data)}건 (종류필터스킵: {skip_type}건)")

    ok = skip = 0
    try:
        cur.executemany(SQL_INSERT, rows_data)
        con.commit()
        ok = len(rows_data)
    except Exception:
        con.rollback()
        for r in rows_data:
            try: cur.execute(SQL_INSERT, r); con.commit(); ok += 1
            except: con.rollback(); skip += 1

    cur.close()
    con.close()
    logger.info(f"{'='*40}")
    logger.info(f"완료: {ok}건 INSERT / {skip}건 스킵")


if __name__ == "__main__":
    asyncio.run(main())