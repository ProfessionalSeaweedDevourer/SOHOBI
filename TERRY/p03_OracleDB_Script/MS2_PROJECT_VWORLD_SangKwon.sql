-- =====================================================
-- 골목상권 매출 Oracle 테이블 (CSV 컬럼명 그대로)
-- DBeaver에서 실행
-- =====================================================

DROP TABLE SANGKWON_SALES CASCADE CONSTRAINTS;
DROP VIEW V_SANGKWON_LATEST;
DROP VIEW V_SANGKWON_BY_INDUTY;

CREATE TABLE SANGKWON_SALES (
    기준_년분기_코드          VARCHAR2(6)   NOT NULL,
    행정동_코드               VARCHAR2(10)  NOT NULL,
    행정동_코드_명            VARCHAR2(100),
    서비스_업종_코드          VARCHAR2(20)  NOT NULL,
    서비스_업종_코드_명       VARCHAR2(100),
    당월_매출_금액            NUMBER(20),
    당월_매출_건수            NUMBER(10),
    주중_매출_금액            NUMBER(20),
    주말_매출_금액            NUMBER(20),
    월요일_매출_금액          NUMBER(20),
    화요일_매출_금액          NUMBER(20),
    수요일_매출_금액          NUMBER(20),
    목요일_매출_금액          NUMBER(20),
    금요일_매출_금액          NUMBER(20),
    토요일_매출_금액          NUMBER(20),
    일요일_매출_금액          NUMBER(20),
    남성_매출_금액            NUMBER(20),
    여성_매출_금액            NUMBER(20),
    연령대_10_매출_금액       NUMBER(20),
    연령대_20_매출_금액       NUMBER(20),
    연령대_30_매출_금액       NUMBER(20),
    연령대_40_매출_금액       NUMBER(20),
    연령대_50_매출_금액       NUMBER(20),
    연령대_60_이상_매출_금액  NUMBER(20),
    CONSTRAINT PK_SANGKWON_SALES PRIMARY KEY (기준_년분기_코드, 행정동_코드, 서비스_업종_코드)
);

CREATE INDEX IDX_SALES_DONG  ON SANGKWON_SALES(행정동_코드);
CREATE INDEX IDX_SALES_YYQU  ON SANGKWON_SALES(기준_년분기_코드);
CREATE INDEX IDX_SALES_INDUTY ON SANGKWON_SALES(서비스_업종_코드);

-- 행정동별 합산 뷰 (최신 분기)
CREATE OR REPLACE VIEW V_SANGKWON_LATEST AS
SELECT
    행정동_코드,
    행정동_코드_명,
    기준_년분기_코드,
    SUM(당월_매출_금액)      AS TOT_SALES_AMT,
    SUM(당월_매출_건수)      AS TOT_SELNG_CO,
    SUM(남성_매출_금액)      AS ML_SALES_AMT,
    SUM(여성_매출_금액)      AS FML_SALES_AMT,
    SUM(주중_매출_금액)      AS MDWK_SALES_AMT,
    SUM(주말_매출_금액)      AS WKEND_SALES_AMT,
    SUM(연령대_20_매출_금액) AS AGE20_AMT,
    SUM(연령대_30_매출_금액) AS AGE30_AMT,
    SUM(연령대_40_매출_금액) AS AGE40_AMT,
    SUM(연령대_50_매출_금액) AS AGE50_AMT
FROM SANGKWON_SALES
WHERE 기준_년분기_코드 = (
    SELECT MAX(기준_년분기_코드) FROM SANGKWON_SALES
)
GROUP BY 행정동_코드, 행정동_코드_명, 기준_년분기_코드;

-- 업종별 뷰 (최신 분기)
CREATE OR REPLACE VIEW V_SANGKWON_BY_INDUTY AS
SELECT
    행정동_코드,
    행정동_코드_명,
    서비스_업종_코드,
    서비스_업종_코드_명,
    기준_년분기_코드,
    당월_매출_금액,
    당월_매출_건수,
    남성_매출_금액,
    여성_매출_금액,
    주중_매출_금액,
    주말_매출_금액
FROM SANGKWON_SALES
WHERE 기준_년분기_코드 = (
    SELECT MAX(기준_년분기_코드) FROM SANGKWON_SALES
);

SELECT SANGKWON_SALES, COUNT(*) AS 건수
FROM SANGKWON_SALES
GROUP BY 상가업소번호
HAVING COUNT(*) > 1;
