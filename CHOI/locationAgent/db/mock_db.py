"""
mock_db.py
SQLite 목업 DB — 상권 단위 (VwsmTrdarSelngQq 기준)
Oracle 전환 시 이 파일 교체
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "commercial.db")


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS commercial_sales (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            quarter       TEXT NOT NULL,
            trdar_code    TEXT NOT NULL,
            trdar_name    TEXT NOT NULL,
            trdar_type    TEXT NOT NULL,
            industry_code TEXT NOT NULL,
            industry_name TEXT NOT NULL,
            monthly_sales INTEGER DEFAULT 0,
            monthly_tx    INTEGER DEFAULT 0,
            weekday_sales INTEGER DEFAULT 0,
            weekend_sales INTEGER DEFAULT 0,
            mon_sales     INTEGER DEFAULT 0,
            tue_sales     INTEGER DEFAULT 0,
            wed_sales     INTEGER DEFAULT 0,
            thu_sales     INTEGER DEFAULT 0,
            fri_sales     INTEGER DEFAULT 0,
            sat_sales     INTEGER DEFAULT 0,
            sun_sales     INTEGER DEFAULT 0,
            time_00_06    INTEGER DEFAULT 0,
            time_06_11    INTEGER DEFAULT 0,
            time_11_14    INTEGER DEFAULT 0,
            time_14_17    INTEGER DEFAULT 0,
            time_17_21    INTEGER DEFAULT 0,
            time_21_24    INTEGER DEFAULT 0,
            male_sales    INTEGER DEFAULT 0,
            female_sales  INTEGER DEFAULT 0,
            age_10s       INTEGER DEFAULT 0,
            age_20s       INTEGER DEFAULT 0,
            age_30s       INTEGER DEFAULT 0,
            age_40s       INTEGER DEFAULT 0,
            age_50s       INTEGER DEFAULT 0,
            age_60s       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS commercial_store (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            quarter       TEXT NOT NULL,
            trdar_code    TEXT NOT NULL,
            trdar_name    TEXT NOT NULL,
            trdar_type    TEXT NOT NULL,
            industry_code TEXT NOT NULL,
            industry_name TEXT NOT NULL,
            store_count   INTEGER DEFAULT 0,
            open_rate     REAL DEFAULT 0.0,
            close_rate    REAL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_sales_lookup
            ON commercial_sales (quarter, trdar_code, industry_code);
        CREATE INDEX IF NOT EXISTS idx_store_lookup
            ON commercial_store (quarter, trdar_code, industry_code);
    """)
    conn.commit()


def insert_sample_data(conn: sqlite3.Connection):
    # (quarter, trdar_code, trdar_name, trdar_type, industry_code, industry_name,
    #  monthly_sales, monthly_tx,
    #  weekday, weekend,
    #  mon, tue, wed, thu, fri, sat, sun,
    #  t00_06, t06_11, t11_14, t14_17, t17_21, t21_24,
    #  male, female,
    #  age10, age20, age30, age40, age50, age60)
    sales_data = [
        # 홍대입구역(홍대) 카페
        ("20253","3120103","홍대입구역(홍대)","발달상권","CS100010","커피-음료",
         32000000000, 920000,
         20000000000, 12000000000,
         3500000000, 2800000000, 3200000000, 3000000000, 4200000000, 6000000000, 6000000000,
         500000000, 3000000000, 7000000000, 5000000000, 9000000000, 7500000000,
         14000000000, 16000000000,
         500000000, 10000000000, 9000000000, 6000000000, 4000000000, 2500000000),
        # 서교동(홍대) 카페
        ("20253","3120102","서교동(홍대)","발달상권","CS100010","커피-음료",
         18000000000, 530000,
         11000000000, 7000000000,
         1800000000, 1500000000, 1800000000, 1700000000, 2500000000, 3500000000, 3200000000,
         200000000, 1500000000, 4000000000, 3000000000, 5000000000, 4300000000,
         7500000000, 9500000000,
         300000000, 6000000000, 5000000000, 3500000000, 2000000000, 1200000000),
        # 연남동(홍대) 카페
        ("20253","3120104","연남동(홍대)","발달상권","CS100010","커피-음료",
         14000000000, 420000,
         8500000000, 5500000000,
         1400000000, 1200000000, 1400000000, 1300000000, 2000000000, 2800000000, 2900000000,
         100000000, 1000000000, 3000000000, 2500000000, 4000000000, 3400000000,
         5500000000, 8500000000,
         200000000, 5000000000, 4000000000, 2500000000, 1500000000, 800000000),
        # 상수역(홍대) 카페
        ("20253","3120105","상수역(홍대)","발달상권","CS100010","커피-음료",
         8000000000, 240000,
         5000000000, 3000000000,
         800000000, 700000000, 800000000, 750000000, 1100000000, 1500000000, 1350000000,
         50000000, 500000000, 1800000000, 1500000000, 2300000000, 1850000000,
         3000000000, 5000000000,
         100000000, 2800000000, 2300000000, 1500000000, 800000000, 500000000),
        # 강남역 한식
        ("20253","3120189","강남역","발달상권","CS100001","한식음식점",
         95000000000, 2500000,
         70000000000, 25000000000,
         13000000000, 11000000000, 13000000000, 12000000000, 17000000000, 14000000000, 15000000000,
         1000000000, 8000000000, 22000000000, 18000000000, 28000000000, 18000000000,
         55000000000, 40000000000,
         2000000000, 18000000000, 35000000000, 22000000000, 12000000000, 6000000000),
        # 잠실역 치킨
        ("20253","3120227","잠실역","발달상권","CS100007","치킨전문점",
         18000000000, 420000,
         10000000000, 8000000000,
         1500000000, 1300000000, 1500000000, 1400000000, 2100000000, 4000000000, 4200000000,
         100000000, 500000000, 2000000000, 2500000000, 7000000000, 5900000000,
         10000000000, 8000000000,
         500000000, 5000000000, 7000000000, 3500000000, 1500000000, 500000000),
    ]

    store_data = [
        # (quarter, trdar_code, trdar_name, trdar_type, industry_code, industry_name,
        #  store_count, open_rate, close_rate)
        ("20253","3120103","홍대입구역(홍대)","발달상권","CS100010","커피-음료",   320, 2.3, 2.0),
        ("20253","3120102","서교동(홍대)",    "발달상권","CS100010","커피-음료",   180, 1.9, 1.6),
        ("20253","3120104","연남동(홍대)",    "발달상권","CS100010","커피-음료",   140, 2.5, 2.1),
        ("20253","3120105","상수역(홍대)",    "발달상권","CS100010","커피-음료",    90, 1.8, 1.5),
        ("20253","3120189","강남역",          "발달상권","CS100001","한식음식점",  890, 1.2, 1.0),
        ("20253","3120227","잠실역",          "발달상권","CS100007","치킨전문점",  180, 1.6, 1.4),
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO commercial_sales
        (quarter, trdar_code, trdar_name, trdar_type, industry_code, industry_name,
         monthly_sales, monthly_tx,
         weekday_sales, weekend_sales,
         mon_sales, tue_sales, wed_sales, thu_sales, fri_sales, sat_sales, sun_sales,
         time_00_06, time_06_11, time_11_14, time_14_17, time_17_21, time_21_24,
         male_sales, female_sales,
         age_10s, age_20s, age_30s, age_40s, age_50s, age_60s)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, sales_data)

    conn.executemany("""
        INSERT OR IGNORE INTO commercial_store
        (quarter, trdar_code, trdar_name, trdar_type, industry_code, industry_name,
         store_count, open_rate, close_rate)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, store_data)

    conn.commit()
    print(f"샘플 데이터 적재 완료: 매출 {len(sales_data)}건 / 점포 {len(store_data)}건")


def init_db():
    # 기존 DB 삭제 후 재생성 (스키마 변경됐으므로)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("기존 DB 삭제")
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    insert_sample_data(conn)
    conn.close()
    print(f"DB 초기화 완료: {DB_PATH}")


if __name__ == "__main__":
    init_db()
