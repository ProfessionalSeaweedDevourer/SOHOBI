import pandas as pd
import sqlite3
import os

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALES_CSV = os.path.join(BASE_DIR, "data", "서울시 상권분석서비스(추정매출-상권)_2024년.csv")
STORE_CSV = os.path.join(BASE_DIR, "data", "store_2024.csv")
DB_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commercial.db")

# ── 매출 CSV ──
print("매출 CSV 읽는 중...")
df_sales = pd.read_csv(SALES_CSV, encoding="cp949")
print(f"  {len(df_sales)}행 로드")

df_sales = df_sales.rename(columns={
    '기준_년분기_코드':         'quarter',
    '상권_구분_코드':           'trdar_type_code',
    '상권_구분_코드_명':        'trdar_type',
    '상권_코드':                'trdar_code',
    '상권_코드_명':             'trdar_name',
    '서비스_업종_코드':         'industry_code',
    '서비스_업종_코드_명':      'industry_name',
    '당월_매출_금액':           'monthly_sales',
    '당월_매출_건수':           'monthly_tx',
    '주중_매출_금액':           'weekday_sales',
    '주말_매출_금액':           'weekend_sales',
    '월요일_매출_금액':         'mon_sales',
    '화요일_매출_금액':         'tue_sales',
    '수요일_매출_금액':         'wed_sales',
    '목요일_매출_금액':         'thu_sales',
    '금요일_매출_금액':         'fri_sales',
    '토요일_매출_금액':         'sat_sales',
    '일요일_매출_금액':         'sun_sales',
    '시간대_00~06_매출_금액':   'time_00_06',
    '시간대_06~11_매출_금액':   'time_06_11',
    '시간대_11~14_매출_금액':   'time_11_14',
    '시간대_14~17_매출_금액':   'time_14_17',
    '시간대_17~21_매출_금액':   'time_17_21',
    '시간대_21~24_매출_금액':   'time_21_24',
    '남성_매출_금액':           'male_sales',
    '여성_매출_금액':           'female_sales',
    '연령대_10_매출_금액':      'age_10s',
    '연령대_20_매출_금액':      'age_20s',
    '연령대_30_매출_금액':      'age_30s',
    '연령대_40_매출_금액':      'age_40s',
    '연령대_50_매출_금액':      'age_50s',
    '연령대_60_이상_매출_금액': 'age_60s',
})

sales_cols = [
    'quarter', 'trdar_code', 'trdar_name', 'trdar_type', 'industry_code', 'industry_name',
    'monthly_sales', 'monthly_tx',
    'weekday_sales', 'weekend_sales',
    'mon_sales', 'tue_sales', 'wed_sales', 'thu_sales', 'fri_sales', 'sat_sales', 'sun_sales',
    'time_00_06', 'time_06_11', 'time_11_14', 'time_14_17', 'time_17_21', 'time_21_24',
    'male_sales', 'female_sales',
    'age_10s', 'age_20s', 'age_30s', 'age_40s', 'age_50s', 'age_60s',
]
df_sales = df_sales[sales_cols].copy()
df_sales['quarter']    = df_sales['quarter'].astype(str)
df_sales['trdar_code'] = df_sales['trdar_code'].astype(str)

# ── 점포 CSV ──
print("점포 CSV 읽는 중...")
df_store = pd.read_csv(STORE_CSV, encoding="utf-8-sig")
print(f"  {len(df_store)}행 로드")

df_store = df_store.rename(columns={
    'STDR_YYQU_CD':   'quarter',
    'TRDAR_SE_CD_NM': 'trdar_type',
    'TRDAR_CD':       'trdar_code',
    'TRDAR_CD_NM':    'trdar_name',
    'SVC_INDUTY_CD':  'industry_code',
    'SVC_INDUTY_CD_NM': 'industry_name',
    'STOR_CO':        'store_count',
    'OPBIZ_RT':       'open_rate',
    'CLSBIZ_RT':      'close_rate',
})

store_cols = [
    'quarter', 'trdar_code', 'trdar_name', 'trdar_type',
    'industry_code', 'industry_name',
    'store_count', 'open_rate', 'close_rate',
]
df_store = df_store[store_cols].copy()
df_store['quarter']    = df_store['quarter'].astype(str)
df_store['trdar_code'] = df_store['trdar_code'].astype(str)

# ── DB 적재 ──
print("\nDB 적재 중...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("  기존 DB 삭제")

conn = sqlite3.connect(DB_PATH)

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

df_sales.to_sql('commercial_sales', conn, if_exists='append', index=False)
print(f"  매출 적재 완료: {len(df_sales)}행")

df_store.to_sql('commercial_store', conn, if_exists='append', index=False)
print(f"  점포 적재 완료: {len(df_store)}행")

conn.commit()
conn.close()
print(f"\n✅ DB 생성 완료: {DB_PATH}")