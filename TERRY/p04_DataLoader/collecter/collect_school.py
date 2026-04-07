# =====================================================
# 학교 정보 수집 + 카카오 좌표 변환 → Oracle INSERT
# 위치: p04_DataLoader/collecter/collect_school.py
#
# 사용법:
#   python collect_school.py           ← 전체 수집 + 좌표 변환
#   python collect_school.py --coord   ← 좌표만 보완 (기수집 데이터)
# =====================================================

import os, sys, asyncio, logging
import xml.etree.ElementTree as ET
import httpx, oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
SEOUL_KEY = os.getenv("SEOUL_SCHOOL_API_KEY", "6e626d744d777374373748684e7575")
KAKAO_KEY = os.getenv("KAKAO_REST_KEY", "064e455e57b72a7665be2ff5515aead2")
BASE_URL = f"http://openapi.seoul.go.kr:8088/{SEOUL_KEY}/xml/neisSchoolInfo"
KAKAO_URL = "https://dapi.kakao.com/v2/local/search/address.json"
PAGE_SIZE = 1000

SQL_MERGE = """
    INSERT INTO SCHOOL_SEOUL (
        ATPT_OFCDC_SC_CODE, ATPT_OFCDC_SC_NM, SD_SCHUL_CODE, SCHUL_NM,
        ENG_SCHUL_NM, SCHUL_KND_SC_NM, LCTN_SC_NM, JU_ORG_NM,
        FOND_SC_NM, ORG_RDNZC, ORG_RDNMA, ORG_RDNDA,
        ORG_TELNO, HMPG_ADRES, COEDU_SC_NM, ORG_FAXNO,
        HS_SC_NM, INDST_SPECL_CCCCL_EXST_YN, HS_GNRL_BUSNS_SC_NM,
        SPCLY_PURPS_HS_ORD_NM, ENE_BFE_SEHF_SC_NM, DGHT_SC_NM,
        FOND_YMD, FOAS_MEMRD, DGHT_CRSE_SC_NM, ORD_SC_NM,
        DDDEP_NM, LOAD_DTM
    ) VALUES (
        :1, :2, :3, :4, :5, :6, :7, :8,
        :9, :10, :11, :12, :13, :14, :15, :16,
        :17, :18, :19, :20, :21, :22,
        :23, :24, :25, :26, :27, :28
    )
"""

SQL_UPDATE_COORD = """
    UPDATE SCHOOL_SEOUL SET MAP_X=:1, MAP_Y=:2 WHERE SD_SCHUL_CODE=:3
"""


def g(item, tag):
    return (item.findtext(tag) or "").strip() or None


async def fetch_page(client, start, end):
    try:
        r = await client.get(f"{BASE_URL}/{start}/{end}/", timeout=20)
        root = ET.fromstring(r.text)
        total = int(root.findtext(".//list_total_count") or 0)
        return total, root.findall(".//row")
    except Exception as e:
        logger.error(f"fetch_page 오류: {e}")
        return 0, []


async def kakao_coord(client, address):
    """카카오 주소→좌표 변환"""
    if not address:
        return None, None
    try:
        r = await client.get(
            KAKAO_URL,
            params={"query": address, "size": 1},
            headers={"Authorization": f"KakaoAK {KAKAO_KEY}"},
            timeout=5,
        )
        docs = r.json().get("documents", [])
        if docs:
            return float(docs[0]["x"]), float(docs[0]["y"])
    except Exception:
        pass
    return None, None


async def main():
    coord_only = "--coord" in sys.argv

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    if not coord_only:
        # ── 1. 학교 목록 수집 ───────────────────────────────────
        async with httpx.AsyncClient() as client:
            total, _ = await fetch_page(client, 1, 1)
            total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
            logger.info(f"전체: {total}건 / {total_pages}페이지")

            all_rows = []
            for page in range(total_pages):
                start = page * PAGE_SIZE + 1
                end = (page + 1) * PAGE_SIZE
                _, rows = await fetch_page(client, start, end)
                all_rows.extend(rows)
                logger.info(f"  페이지 {page+1}/{total_pages}: {len(rows)}건")
                await asyncio.sleep(0.2)

        rows_data = [
            (
                g(row, "ATPT_OFCDC_SC_CODE"),
                g(row, "ATPT_OFCDC_SC_NM"),
                g(row, "SD_SCHUL_CODE"),
                g(row, "SCHUL_NM"),
                g(row, "ENG_SCHUL_NM"),
                g(row, "SCHUL_KND_SC_NM"),
                g(row, "LCTN_SC_NM"),
                g(row, "JU_ORG_NM"),
                g(row, "FOND_SC_NM"),
                g(row, "ORG_RDNZC"),
                g(row, "ORG_RDNMA"),
                g(row, "ORG_RDNDA"),
                g(row, "ORG_TELNO"),
                g(row, "HMPG_ADRES"),
                g(row, "COEDU_SC_NM"),
                g(row, "ORG_FAXNO"),
                g(row, "HS_SC_NM"),
                g(row, "INDST_SPECL_CCCCL_EXST_YN"),
                g(row, "HS_GNRL_BUSNS_SC_NM"),
                g(row, "SPCLY_PURPS_HS_ORD_NM"),
                g(row, "ENE_BFE_SEHF_SC_NM"),
                g(row, "DGHT_SC_NM"),
                g(row, "FOND_YMD"),
                g(row, "FOAS_MEMRD"),
                g(row, "DGHT_CRSE_SC_NM"),
                g(row, "ORD_SC_NM"),
                g(row, "DDDEP_NM"),
                g(row, "LOAD_DTM"),
            )
            for row in all_rows
            if g(row, "SD_SCHUL_CODE")
        ]

        ok = skip = 0
        try:
            cur.executemany(SQL_MERGE, rows_data)
            con.commit()
            ok = len(rows_data)
        except Exception as e:
            con.rollback()
            logger.error(f"배치 오류: {e}")
            for r in rows_data:
                try:
                    cur.execute(SQL_MERGE, r)
                    con.commit()
                    ok += 1
                except:
                    con.rollback()
                    skip += 1
        logger.info(f"INSERT: {ok}건 / 스킵: {skip}건")

    # ── 2. 좌표 변환 (카카오) ────────────────────────────────────
    logger.info("좌표 변환 시작 (카카오 주소검색)...")
    rows = cur.execute(
        "SELECT SD_SCHUL_CODE, ORG_RDNMA FROM SCHOOL_SEOUL WHERE MAP_X IS NULL AND ORG_RDNMA IS NOT NULL"
    ).fetchall()
    logger.info(f"좌표 미입력: {len(rows)}건")

    BATCH = 10
    total_ok = 0
    async with httpx.AsyncClient() as client:
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            tasks = [kakao_coord(client, r[1]) for r in batch]
            results = await asyncio.gather(*tasks)
            for (code, addr), (x, y) in zip(batch, results):
                if x and y:
                    cur.execute(SQL_UPDATE_COORD, [x, y, code])
                    total_ok += 1
            con.commit()
            if (i // BATCH) % 10 == 0:
                logger.info(
                    f"  좌표 변환 {min(i+BATCH, len(rows))}/{len(rows)}건 (성공: {total_ok}건)"
                )
            await asyncio.sleep(0.3)

    logger.info(f"좌표 변환 완료: {total_ok}/{len(rows)}건")
    cur.close()
    con.close()


if __name__ == "__main__":
    asyncio.run(main())
