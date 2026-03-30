# =====================================================
# 소상공인 상권정보 CSV → STORE_SEOUL (영문 컬럼) INSERT
# 실행: python load_store_csv.py [CSV 파일 경로]
#
# 원본 CSV 컬럼 (소상공인진흥공단 제공):
#   상가업소번호, 상호명, 지점명, 상권업종대분류코드, 상권업종대분류명,
#   상권업종중분류코드, 상권업종중분류명, 상권업종소분류코드, 상권업종소분류명,
#   표준산업분류코드, 표준산업분류명, 시도코드, 시도명, 시군구코드, 시군구명,
#   행정동코드, 행정동명, 법정동코드, 법정동명, 지번코드, 대지구분코드, 대지구분명,
#   지번본번지, 지번부번지, 지번주소, 도로명코드, 도로명, 건물본번지, 건물부번지,
#   건물관리번호, 건물명, 도로명주소, 구우편번호, 신우편번호,
#   동정보, 층정보, 호정보, 경도, 위도
#
# 대상 테이블: STORE_SEOUL (영문 컬럼)
# =====================================================
# cd p04_DataLoader
# python load_store_csv.py "csv/location_csv/소상공인시장진흥공단_상가(상권)정보_전북_202512.csv"

import os
import sys
import csv
import logging
import oracledb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── DB 접속 정보 ──────────────────────────────────────────────
DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"
BATCH_SIZE = 1000  # 한 번에 INSERT할 건수

# ── 원본 CSV 컬럼 → DB 컬럼 매핑 ──────────────────────────────
COL_MAP = {
    "상가업소번호": "STORE_ID",
    "상호명": "STORE_NM",
    "지점명": "BRANCH_NM",
    "상권업종대분류코드": "CAT_CD",
    "상권업종대분류명": "CAT_NM",
    "상권업종중분류코드": "MID_CAT_CD",
    "상권업종중분류명": "MID_CAT_NM",
    "상권업종소분류코드": "SUB_CAT_CD",
    "상권업종소분류명": "SUB_CAT_NM",
    "표준산업분류코드": "STD_IND_CD",
    "표준산업분류명": "STD_IND_NM",
    "시도코드": "SIDO_CD",
    "시도명": "SIDO_NM",
    "시군구코드": "SGG_CD",
    "시군구명": "SGG_NM",
    "행정동코드": "ADM_CD",
    "행정동명": "ADM_NM",
    "법정동코드": "LEGAL_CD",
    "법정동명": "LEGAL_NM",
    "지번코드": "JIBUN_CD",
    "대지구분코드": "LAND_TYPE_CD",
    "대지구분명": "LAND_TYPE_NM",
    "지번본번지": "JIBUN_MAIN",
    "지번부번지": "JIBUN_SUB",
    "지번주소": "JIBUN_ADDR",
    "도로명코드": "ROAD_CD",
    "도로명": "ROAD_NM",
    "건물본번지": "BLDG_MAIN",
    "건물부번지": "BLDG_SUB",
    "건물관리번호": "BLDG_MGT_NO",
    "건물명": "BLDG_NM",
    "도로명주소": "ROAD_ADDR",
    "구우편번호": "OLD_ZIP",
    "신우편번호": "NEW_ZIP",
    "동정보": "DONG_INFO",
    "층정보": "FLOOR_INFO",
    "호정보": "UNIT_INFO",
    "경도": "LNG",
    "위도": "LAT",
}

# 시도명 → 테이블명
SIDO_TABLE = {
    "서울특별시": "STORE_SEOUL",
    "경기도": "STORE_GYEONGGI",
    "인천광역시": "STORE_INCHEON",
    "부산광역시": "STORE_BUSAN",
    "대구광역시": "STORE_DAEGU",
    "광주광역시": "STORE_GWANGJU",
    "대전광역시": "STORE_DAEJEON",
    "울산광역시": "STORE_ULSAN",
    "강원특별자치도": "STORE_GANGWON",
    "강원도": "STORE_GANGWON",
    "충청북도": "STORE_CHUNGBUK",
    "충청남도": "STORE_CHUNGNAM",
    "전라북도": "STORE_JEONBUK",
    "전북특별자치도": "STORE_JEONBUK",
    "전라남도": "STORE_JEONNAM",
    "경상북도": "STORE_GYEONGBUK",
    "경상남도": "STORE_GYEONGNAM",
    "제주특별자치도": "STORE_JEJU",
}

DB_COLS = list(COL_MAP.values())
PLACEHOLDERS = ", ".join([f":{i+1}" for i in range(len(DB_COLS))])


def make_sql(table):
    # 단순 INSERT - 중복 시 예외 발생하면 스킵 처리
    cols_str = ", ".join(DB_COLS)
    vals_str = ", ".join([f":{i+1}" for i in range(len(DB_COLS))])
    return f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str})"


def parse_row(row, col_idx):
    """CSV 행 → DB INSERT용 튜플 변환"""
    vals = []
    for kor, eng in COL_MAP.items():
        idx = col_idx.get(kor)
        if idx is None:
            vals.append(None)
            continue
        v = row[idx].strip() if idx < len(row) else None
        # 경도/위도는 float
        if eng in ("LNG", "LAT"):
            try:
                vals.append(float(v) if v else None)
            except:
                vals.append(None)
        else:
            vals.append(v if v else None)
    return tuple(vals)


def load_csv(csv_path: str, target_table: str = None):
    """
    CSV 파일 → Oracle MERGE INSERT
    target_table: 지정 시 해당 테이블만, None이면 시도명 자동 감지
    """
    if not os.path.exists(csv_path):
        logger.error(f"파일 없음: {csv_path}")
        return

    logger.info(f"로드 시작: {csv_path}")

    # ── 인코딩 자동 감지 ──
    encoding = "utf-8-sig"
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            f.read(1024)
    except UnicodeDecodeError:
        encoding = "cp949"
    logger.info(f"인코딩: {encoding}")

    def get_con():
        """DB 연결 (재연결 지원)"""
        return oracledb.connect(DB_INFO)

    con = get_con()
    cur = con.cursor()

    total = 0
    error = 0
    batch_data = {}  # table → list of tuples

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)
        col_idx = {h.strip(): i for i, h in enumerate(headers)}

        # 컬럼 검증
        missing = [k for k in COL_MAP if k not in col_idx]
        if missing:
            logger.warning(f"누락 컬럼 {len(missing)}개: {missing[:5]}...")

        sido_idx = col_idx.get("시도명")

        for row in reader:
            try:
                # 테이블 결정
                if target_table:
                    table = target_table
                else:
                    sido = row[sido_idx].strip() if sido_idx is not None else ""
                    table = SIDO_TABLE.get(sido, "STORE_SEOUL")

                vals = parse_row(row, col_idx)
                if table not in batch_data:
                    batch_data[table] = []
                batch_data[table].append(vals)

                # 배치 처리
                for tbl, rows in batch_data.items():
                    if len(rows) >= BATCH_SIZE:
                        sql = make_sql(tbl)
                        # 연결 끊기면 재연결
                        for attempt in range(3):
                            try:
                                cur.executemany(sql, rows)
                                con.commit()
                                break
                            except Exception as e:
                                if "not connected" in str(
                                    e
                                ).lower() or "DPY-1001" in str(e):
                                    logger.warning(
                                        f"연결 끊김, 재연결 시도 {attempt+1}/3..."
                                    )
                                    try:
                                        cur.close()
                                        con.close()
                                    except:
                                        pass
                                    con = get_con()
                                    cur = con.cursor()
                                elif (
                                    "ORA-00001" in str(e) or "unique" in str(e).lower()
                                ):
                                    # 중복 키 → 개별 INSERT로 스킵 처리
                                    con.rollback()
                                    for r in rows:
                                        try:
                                            cur.execute(sql, r)
                                            con.commit()
                                        except Exception:
                                            con.rollback()
                                    break
                                else:
                                    raise
                        total += len(rows)
                        logger.info(f"[{tbl}] {total:,}건 INSERT")
                        batch_data[tbl] = []

            except Exception as e:
                error += 1
                if error <= 5:
                    logger.error(f"행 오류: {e} / {row[:3]}")

    # 남은 배치 처리
    for tbl, rows in batch_data.items():
        if rows:
            try:
                sql = make_sql(tbl)
                cur.executemany(sql, rows)
                con.commit()
                total += len(rows)
                logger.info(f"[{tbl}] 최종 {total:,}건 INSERT")
            except Exception as e:
                logger.error(f"최종 배치 오류: {e}")

    cur.close()
    con.close()
    logger.info(f"✅ 완료: 성공 {total:,}건 / 오류 {error}건")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python load_store_csv.py <CSV파일경로> [테이블명]")
        print("  예시: python load_store_csv.py 소상공인_서울.csv STORE_SEOUL")
        print("  테이블명 생략 시 시도명 자동 감지")
        sys.exit(1)

    csv_file = sys.argv[1]
    table = sys.argv[2] if len(sys.argv) > 2 else None
    load_csv(csv_file, table)
