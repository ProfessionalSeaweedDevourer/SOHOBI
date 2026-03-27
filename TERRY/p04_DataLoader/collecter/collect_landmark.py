# =====================================================
# 한국관광공사 서울 랜드마크 수집 → Oracle INSERT
# 위치: p04_DataLoader/collector/collect_landmark.py
#
# 콘텐츠타입: 12(관광지), 14(문화시설), 15(축제)
# 지역코드: 1(서울)
#
# 사용법:
#   python collect_landmark.py              ← 전체 수집 (최초 1회)
#   python collect_landmark.py --type=12    ← 관광지만 (고정)
#   python collect_landmark.py --type=14    ← 문화시설만 (고정)
#   python collect_landmark.py --no-detail  ← 상세 조회 스킵 (429 방지)
#   python collect_landmark.py --type=15    ← 축제만 (주기적 갱신)
#   python collect_landmark.py --festival   ← 축제만 갱신 (월 1회 권장)
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

# ── 설정 ──────────────────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
KTO_KEY = os.getenv(
    "KTO_GW_INFO_KEY",
    "b7906dd729da8d6d4f67bd6bed484f032f9f586abc7b382b41b93a003949385e",
)
BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
AREA_CODE = "1"  # 서울
PAGE_SIZE = 1000
CONTENT_TYPES = ["12", "14"]  # 관광지, 문화시설 (축제는 백엔드 실시간 API)

# 고정 타입(12,14): 없으면 INSERT
SQL_MERGE = """
    INSERT INTO LANDMARK (
        CONTENT_ID, CONTENT_TYPE_ID, TITLE, ADDR1, ADDR2,
        AREA_CODE, SIGUNGU_CODE, CAT1, CAT2, CAT3,
        MAP_X, MAP_Y, FIRST_IMAGE, FIRST_IMAGE2, TEL,
        HOMEPAGE, OVERVIEW
    ) VALUES (
        :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15,
        :16, :17
    )
"""

# 축제 타입(15): UPSERT (갱신)
SQL_UPSERT = """
    MERGE INTO LANDMARK t
    USING (SELECT :1 AS CONTENT_ID FROM DUAL) s
    ON (t.CONTENT_ID = s.CONTENT_ID)
    WHEN MATCHED THEN UPDATE SET
        TITLE=:3, ADDR1=:4, ADDR2=:5, SIGUNGU_CODE=:7,
        MAP_X=:11, MAP_Y=:12, FIRST_IMAGE=:13, FIRST_IMAGE2=:14, TEL=:15,
        LOAD_DT=SYSDATE
    WHEN NOT MATCHED THEN INSERT (
        CONTENT_ID, CONTENT_TYPE_ID, TITLE, ADDR1, ADDR2,
        AREA_CODE, SIGUNGU_CODE, CAT1, CAT2, CAT3,
        MAP_X, MAP_Y, FIRST_IMAGE, FIRST_IMAGE2, TEL
    ) VALUES (
        :1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15
    )
"""

SQL_UPDATE_DETAIL = """
    UPDATE LANDMARK SET HOMEPAGE=:1, OVERVIEW=:2
    WHERE CONTENT_ID=:3
"""


def g(item, tag):
    return (item.findtext(tag) or "").strip()


def to_float(val):
    try:
        return float(val.strip()) if val.strip() else None
    except:
        return None


async def fetch_list(client, content_type_id, page_no=1):
    """목록 조회"""
    try:
        r = await client.get(
            f"{BASE_URL}/areaBasedList2",
            params={
                "serviceKey": KTO_KEY,
                "numOfRows": PAGE_SIZE,
                "pageNo": page_no,
                "MobileOS": "ETC",
                "MobileApp": "SOHOBI",
                "areaCode": AREA_CODE,
                "contentTypeId": content_type_id,
                "_type": "xml",
            },
            timeout=20,
        )
        root = ET.fromstring(r.text)
        total = int(root.findtext(".//totalCount") or 0)
        items = root.findall(".//item")
        return total, items
    except Exception as e:
        logger.error(f"fetch_list 오류: {e}")
        return 0, []


async def fetch_detail(client, content_id):
    """상세 조회 (홈페이지, 개요)"""
    try:
        r = await client.get(
            f"{BASE_URL}/detailCommon2",
            params={
                "serviceKey": KTO_KEY,
                "contentId": content_id,
                "MobileOS": "ETC",
                "MobileApp": "SOHOBI",
                "defaultYN": "Y",
                "overviewYN": "Y",
                "_type": "xml",
            },
            timeout=15,
        )
        root = ET.fromstring(r.text)
        items = root.findall(".//item")
        return items[0] if items else None
    except Exception as e:
        logger.error(f"fetch_detail 오류: {content_id} / {e}")
        return None


async def collect_type(client, content_type_id, cur, con, no_detail=False):
    """특정 콘텐츠타입 전체 수집"""
    type_name = {"12": "관광지", "14": "문화시설", "15": "축제"}.get(
        content_type_id, content_type_id
    )
    logger.info(f"▶ [{type_name}] 수집 시작...")

    # 1페이지로 전체 건수 확인
    total, _ = await fetch_list(client, content_type_id, 1)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    logger.info(f"  전체: {total}건 / {total_pages}페이지")

    # 전체 페이지 수집
    all_items = []
    for page in range(1, total_pages + 1):
        _, items = await fetch_list(client, content_type_id, page)
        all_items.extend(items)
        logger.info(f"  [{type_name}] 페이지 {page}/{total_pages}: {len(items)}건")
        await asyncio.sleep(0.1)

    # DB INSERT (축제=UPSERT, 나머지=INSERT ONLY)
    sql = SQL_MERGE  # 관광지/문화시설은 INSERT ONLY
    rows = []
    for item in all_items:
        rows.append(
            (
                g(item, "contentid"),
                content_type_id,
                g(item, "title"),
                g(item, "addr1"),
                g(item, "addr2"),
                AREA_CODE,
                g(item, "sigungucode"),
                g(item, "cat1"),
                g(item, "cat2"),
                g(item, "cat3"),
                to_float(g(item, "mapx")),
                to_float(g(item, "mapy")),
                g(item, "firstimage") or None,
                g(item, "firstimage2") or None,
                g(item, "tel") or None,
                None,  # HOMEPAGE (상세 조회 시 업데이트)
                None,  # OVERVIEW (상세 조회 시 업데이트)
            )
        )

    ok = skip = 0
    try:
        cur.executemany(sql, rows)
        con.commit()
        ok = len(rows)
        logger.info(f"  [{type_name}] 배치 INSERT 성공")
    except Exception as e:
        con.rollback()
        logger.warning(f"  [{type_name}] 배치 실패({e}) → 개별 INSERT 시도")
        for r in rows:
            try:
                cur.execute(sql, r)
                con.commit()
                ok += 1
            except Exception as e2:
                con.rollback()
                skip += 1
                if skip <= 3:
                    logger.warning(f"  스킵: {r[0]} / {e2}")

    logger.info(f"  [{type_name}] INSERT: {ok}건 / 스킵: {skip}건")

    # 상세 정보 수집 (홈페이지 + 개요) - 배치 처리로 429 방지
    if no_detail:
        logger.info(f"  [{type_name}] 상세 조회 스킵 (--no-detail)")
        return ok
    logger.info(f"  [{type_name}] 상세 수집 중...")
    detail_ok = 0
    DETAIL_BATCH = 5  # 동시 요청 수 (429 방지용 보수적 설정)
    DETAIL_DELAY = 2.0  # 배치 간 딜레이 (초)

    content_ids = [g(item, "contentid") for item in all_items if g(item, "contentid")]
    details = []
    for i in range(0, len(content_ids), DETAIL_BATCH):
        batch = content_ids[i : i + DETAIL_BATCH]
        batch_results = await asyncio.gather(
            *[fetch_detail(client, cid) for cid in batch]
        )
        details.extend(batch_results)
        logger.info(
            f"  상세 {min(i+DETAIL_BATCH, len(content_ids))}/{len(content_ids)}건"
        )
        if i + DETAIL_BATCH < len(content_ids):
            await asyncio.sleep(DETAIL_DELAY)

    detail_rows = []
    for detail in details:
        if detail:
            detail_rows.append(
                (
                    g(detail, "homepage") or None,
                    g(detail, "overview") or None,
                    g(detail, "contentid"),
                )
            )

    if detail_rows:
        try:
            cur.executemany(SQL_UPDATE_DETAIL, detail_rows)
            con.commit()
            detail_ok = len(detail_rows)
        except Exception as e:
            con.rollback()
            logger.error(f"  상세 업데이트 오류: {e}")

    logger.info(f"  [{type_name}] 상세 업데이트: {detail_ok}건")
    return ok


async def main():
    # 콘텐츠타입 필터
    types = CONTENT_TYPES
    no_detail = False
    for a in sys.argv[1:]:
        if a.startswith("--type="):
            types = [a.split("=")[1]]
        elif a == "--no-detail":
            no_detail = True
    logger.info(f"수집 타입: {types} / 상세조회: {'스킵' if no_detail else '포함'}")

    logger.info(f"수집 타입: {types}")

    con = oracledb.connect(DB_INFO)
    cur = con.cursor()

    async with httpx.AsyncClient() as client:
        total = 0
        for ct in types:
            ok = await collect_type(client, ct, cur, con, no_detail=no_detail)
            total += ok

    cur.close()
    con.close()
    logger.info(f"{'='*40}")
    logger.info(f"완료: 총 {total}건")


if __name__ == "__main__":
    asyncio.run(main())
