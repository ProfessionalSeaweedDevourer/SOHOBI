-- ============================================================
-- SOHOBI — PostgreSQL 스키마
-- Oracle SANGKWON_SALES / SANGKWON_STORE 대응
-- ============================================================

-- sangkwon_sales: 행정동별 업종 매출 데이터
CREATE TABLE IF NOT EXISTS sangkwon_sales (
    id                BIGSERIAL PRIMARY KEY,
    base_yr_qtr_cd    VARCHAR(6)   NOT NULL,   -- 기준 년도 분기 코드 (예: 20244)
    adm_cd            VARCHAR(10)  NOT NULL,   -- 행정동 코드
    adm_nm            VARCHAR(50),             -- 행정동명
    svc_induty_cd     VARCHAR(20)  NOT NULL,   -- 서비스 업종 코드
    svc_induty_nm     VARCHAR(50),             -- 서비스 업종명
    tot_sales_amt     BIGINT,                  -- 월 매출 금액
    tot_selng_co      INTEGER,                 -- 월 매출 건수
    mdwk_sales_amt    BIGINT,                  -- 주중 매출 금액
    wkend_sales_amt   BIGINT,                  -- 주말 매출 금액
    mon_sales_amt     BIGINT,
    tue_sales_amt     BIGINT,
    wed_sales_amt     BIGINT,
    thu_sales_amt     BIGINT,
    fri_sales_amt     BIGINT,
    sat_sales_amt     BIGINT,
    sun_sales_amt     BIGINT,
    tm00_06_sales_amt BIGINT,
    tm06_11_sales_amt BIGINT,
    tm11_14_sales_amt BIGINT,
    tm14_17_sales_amt BIGINT,
    tm17_21_sales_amt BIGINT,
    tm21_24_sales_amt BIGINT,
    ml_sales_amt      BIGINT,                  -- 남성 매출
    fml_sales_amt     BIGINT,                  -- 여성 매출
    age10_amt         BIGINT,
    age20_amt         BIGINT,
    age30_amt         BIGINT,
    age40_amt         BIGINT,
    age50_amt         BIGINT,
    age60_amt         BIGINT
);

CREATE INDEX IF NOT EXISTS idx_sales_lookup
    ON sangkwon_sales (base_yr_qtr_cd, adm_cd, svc_induty_cd);


-- sangkwon_store: 행정동별 업종 점포수 / 개폐업 데이터
CREATE TABLE IF NOT EXISTS sangkwon_store (
    id                    BIGSERIAL PRIMARY KEY,
    base_yr_qtr_cd        VARCHAR(6)   NOT NULL,
    adm_cd                VARCHAR(10)  NOT NULL,
    adm_nm                VARCHAR(50),
    svc_induty_cd         VARCHAR(20)  NOT NULL,
    svc_induty_nm         VARCHAR(50),
    stor_co               INTEGER,               -- 점포 수
    similr_induty_stor_co INTEGER,               -- 유사 업종 점포 수
    opbiz_rt              NUMERIC(6,2),          -- 개업률 (%)
    opbiz_stor_co         INTEGER,               -- 개업 점포 수
    clsbiz_rt             NUMERIC(6,2),          -- 폐업률 (%)
    clsbiz_stor_co        INTEGER,               -- 폐업 점포 수
    frc_stor_co           INTEGER                -- 프랜차이즈 점포 수
);

CREATE INDEX IF NOT EXISTS idx_store_lookup
    ON sangkwon_store (base_yr_qtr_cd, adm_cd, svc_induty_cd);
