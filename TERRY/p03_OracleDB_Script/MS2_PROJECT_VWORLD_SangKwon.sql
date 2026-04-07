-- =====================================================
-- 골목상권 매출 Oracle 테이블 (CSV 53컬럼 완전 매핑)
-- =====================================================

DROP VIEW  V_SANGKWON_BY_INDUTY;
DROP VIEW  V_SANGKWON_LATEST;
DROP TABLE SANGKWON_SALES CASCADE CONSTRAINTS;

CREATE TABLE SANGKWON_SALES (
    -- ── 기준 키 (PK) ─────────────────────────────────
    base_yr_qtr_cd    VARCHAR2(6)   NOT NULL,  -- 기준_년분기_코드
    adm_cd            VARCHAR2(10)  NOT NULL,  -- 행정동_코드
    adm_nm            VARCHAR2(100),           -- 행정동_코드_명
    svc_induty_cd     VARCHAR2(20)  NOT NULL,  -- 서비스_업종_코드
    svc_induty_nm     VARCHAR2(100),           -- 서비스_업종_코드_명

    -- ── 당월 합계 ────────────────────────────────────
    tot_sales_amt     NUMBER(20),              -- 당월_매출_금액
    tot_selng_co      NUMBER(10),              -- 당월_매출_건수

    -- ── 요일별 금액 ──────────────────────────────────
    mdwk_sales_amt    NUMBER(20),              -- 주중_매출_금액
    wkend_sales_amt   NUMBER(20),              -- 주말_매출_금액
    mon_sales_amt     NUMBER(20),              -- 월요일_매출_금액
    tue_sales_amt     NUMBER(20),              -- 화요일_매출_금액
    wed_sales_amt     NUMBER(20),              -- 수요일_매출_금액
    thu_sales_amt     NUMBER(20),              -- 목요일_매출_금액
    fri_sales_amt     NUMBER(20),              -- 금요일_매출_금액
    sat_sales_amt     NUMBER(20),              -- 토요일_매출_금액
    sun_sales_amt     NUMBER(20),              -- 일요일_매출_금액

    -- ── 시간대별 금액 ────────────────────────────────
    tm00_06_sales_amt NUMBER(20),              -- 시간대_00~06_매출_금액
    tm06_11_sales_amt NUMBER(20),              -- 시간대_06~11_매출_금액
    tm11_14_sales_amt NUMBER(20),              -- 시간대_11~14_매출_금액
    tm14_17_sales_amt NUMBER(20),              -- 시간대_14~17_매출_금액
    tm17_21_sales_amt NUMBER(20),              -- 시간대_17~21_매출_금액
    tm21_24_sales_amt NUMBER(20),              -- 시간대_21~24_매출_금액

    -- ── 성별 금액 ────────────────────────────────────
    ml_sales_amt      NUMBER(20),              -- 남성_매출_금액
    fml_sales_amt     NUMBER(20),              -- 여성_매출_금액

    -- ── 연령대별 금액 ────────────────────────────────
    age10_amt         NUMBER(20),              -- 연령대_10_매출_금액
    age20_amt         NUMBER(20),              -- 연령대_20_매출_금액
    age30_amt         NUMBER(20),              -- 연령대_30_매출_금액
    age40_amt         NUMBER(20),              -- 연령대_40_매출_금액
    age50_amt         NUMBER(20),              -- 연령대_50_매출_금액
    age60_amt         NUMBER(20),              -- 연령대_60_이상_매출_금액

    -- ── 요일별 건수 ──────────────────────────────────
    mdwk_selng_co     NUMBER(10),              -- 주중_매출_건수
    wkend_selng_co    NUMBER(10),              -- 주말_매출_건수
    mon_selng_co      NUMBER(10),              -- 월요일_매출_건수
    tue_selng_co      NUMBER(10),              -- 화요일_매출_건수
    wed_selng_co      NUMBER(10),              -- 수요일_매출_건수
    thu_selng_co      NUMBER(10),              -- 목요일_매출_건수
    fri_selng_co      NUMBER(10),              -- 금요일_매출_건수
    sat_selng_co      NUMBER(10),              -- 토요일_매출_건수
    sun_selng_co      NUMBER(10),              -- 일요일_매출_건수

    -- ── 시간대별 건수 ────────────────────────────────
    tm00_06_selng_co  NUMBER(10),              -- 시간대_건수~06_매출_건수
    tm06_11_selng_co  NUMBER(10),              -- 시간대_건수~11_매출_건수
    tm11_14_selng_co  NUMBER(10),              -- 시간대_건수~14_매출_건수
    tm14_17_selng_co  NUMBER(10),              -- 시간대_건수~17_매출_건수
    tm17_21_selng_co  NUMBER(10),              -- 시간대_건수~21_매출_건수
    tm21_24_selng_co  NUMBER(10),              -- 시간대_건수~24_매출_건수

    -- ── 성별 건수 ────────────────────────────────────
    ml_selng_co       NUMBER(10),              -- 남성_매출_건수
    fml_selng_co      NUMBER(10),              -- 여성_매출_건수

    -- ── 연령대별 건수 ────────────────────────────────
    age10_selng_co    NUMBER(10),              -- 연령대_10_매출_건수
    age20_selng_co    NUMBER(10),              -- 연령대_20_매출_건수
    age30_selng_co    NUMBER(10),              -- 연령대_30_매출_건수
    age40_selng_co    NUMBER(10),              -- 연령대_40_매출_건수
    age50_selng_co    NUMBER(10),              -- 연령대_50_매출_건수
    age60_selng_co    NUMBER(10),              -- 연령대_60_이상_매출_건수

    CONSTRAINT PK_SANGKWON_SALES PRIMARY KEY (base_yr_qtr_cd, adm_cd, svc_induty_cd)
);

CREATE INDEX IDX_SANGKWON_ADM    ON SANGKWON_SALES (adm_cd);
CREATE INDEX IDX_SANGKWON_INDUTY ON SANGKWON_SALES (svc_induty_cd);
CREATE INDEX IDX_SANGKWON_QTR    ON SANGKWON_SALES (base_yr_qtr_cd);


-- =====================================================
-- 뷰: 행정동별 최신 분기 합산 (sangkwonDAO.load() 용)
-- =====================================================
CREATE OR REPLACE VIEW V_SANGKWON_LATEST AS
SELECT
    adm_cd,
    adm_nm,
    base_yr_qtr_cd,
    SUM(tot_sales_amt)    AS tot_sales_amt,
    SUM(tot_selng_co)     AS tot_selng_co,
    SUM(ml_sales_amt)     AS ml_sales_amt,
    SUM(fml_sales_amt)    AS fml_sales_amt,
    SUM(mdwk_sales_amt)   AS mdwk_sales_amt,
    SUM(wkend_sales_amt)  AS wkend_sales_amt,
    SUM(age20_amt)        AS age20_amt,
    SUM(age30_amt)        AS age30_amt,
    SUM(age40_amt)        AS age40_amt,
    SUM(age50_amt)        AS age50_amt
FROM SANGKWON_SALES
WHERE base_yr_qtr_cd = (SELECT MAX(base_yr_qtr_cd) FROM SANGKWON_SALES)
GROUP BY adm_cd, adm_nm, base_yr_qtr_cd;


-- =====================================================
-- 뷰: 행정동+업종별 최신 분기 (업종 패널용)
-- =====================================================
CREATE OR REPLACE VIEW V_SANGKWON_BY_INDUTY AS
SELECT
    adm_cd, adm_nm, svc_induty_cd, svc_induty_nm,
    base_yr_qtr_cd,
    tot_sales_amt, tot_selng_co,
    ml_sales_amt, fml_sales_amt,
    mdwk_sales_amt, wkend_sales_amt,
    age20_amt, age30_amt, age40_amt, age50_amt
FROM SANGKWON_SALES
WHERE base_yr_qtr_cd = (SELECT MAX(base_yr_qtr_cd) FROM SANGKWON_SALES);