-- ═══════════════════════════════════════════════════════════════
-- STEP 1: 스테이징 테이블 생성 (CSV 컬럼 그대로)
-- DBeaver에서 law_admin_mapping.csv → 이 테이블로 import
-- ═══════════════════════════════════════════════════════════════
DROP TABLE STG_LAW_ADM;

CREATE TABLE STG_LAW_ADM (
    SIDO_NM     VARCHAR2(20 CHAR),
    SGG_NM      VARCHAR2(30 CHAR),
    LAW_CD      VARCHAR2(10 CHAR),
    LAW_NM      VARCHAR2(50 CHAR),
    ADM_CD      VARCHAR2(15 CHAR),
    ADM_NM      VARCHAR2(50 CHAR),
    MATCH_TYPE  VARCHAR2(20 CHAR),
    CONFIDENCE  VARCHAR2(10 CHAR)
);
ALTER TABLE STG_LAW_ADM MODIFY SIDO_NM VARCHAR2(20 CHAR);
ALTER TABLE STG_LAW_ADM MODIFY SGG_NM VARCHAR2(30 CHAR);
ALTER TABLE STG_LAW_ADM MODIFY LAW_NM VARCHAR2(50 CHAR);
ALTER TABLE STG_LAW_ADM MODIFY ADM_NM VARCHAR2(50 CHAR);
ALTER TABLE STG_LAW_ADM MODIFY CONFIDENCE VARCHAR2(10 CHAR);
-- ═══════════════════════════════════════════════════════════════
-- STEP 2: CSV import 후 실행 - 메인 테이블 생성 및 데이터 이관
-- ═══════════════════════════════════════════════════════════════

-- 2-1. 법정동 마스터 (서울만, 중복제거)
CREATE TABLE LAW_DONG_SEOUL (
    LAW_CD   VARCHAR2(10) PRIMARY KEY,
    EMD_CD   VARCHAR2(8)  NOT NULL,   -- WFS emd_cd = LAW_CD 앞 8자리
    GU_NM    VARCHAR2(20) NOT NULL,
    LAW_NM   VARCHAR2(30) NOT NULL
);
CREATE INDEX IDX_LDS_EMD ON LAW_DONG_SEOUL(EMD_CD);
CREATE INDEX IDX_LDS_GU  ON LAW_DONG_SEOUL(GU_NM);

INSERT INTO LAW_DONG_SEOUL
SELECT DISTINCT
    LAW_CD,
    SUBSTR(LAW_CD, 1, 8)  AS EMD_CD,
    SGG_NM                AS GU_NM,
    LAW_NM
FROM STG_LAW_ADM
WHERE SIDO_NM = '서울특별시'
  AND LAW_CD IS NOT NULL;

COMMIT;


-- 2-2. 법정동→행정동 매핑 (1:N)
CREATE TABLE LAW_ADM_MAP (
    LAW_CD      VARCHAR2(10) NOT NULL,
    ADM_CD      VARCHAR2(8)  NOT NULL,
    ADM_NM      VARCHAR2(30) NOT NULL,
    MATCH_TYPE  VARCHAR2(20),
    CONFIDENCE  NUMBER(3,2),
    CONSTRAINT PK_LAW_ADM PRIMARY KEY (LAW_CD, ADM_CD)
);
CREATE INDEX IDX_LAM_ADM ON LAW_ADM_MAP(ADM_CD);

INSERT INTO LAW_ADM_MAP
SELECT
    LAW_CD,
    REGEXP_REPLACE(ADM_CD, '\.0$', '')  AS ADM_CD,   -- 소수점 제거 "11230680.0" → "11230680"
    ADM_NM,
    MATCH_TYPE,
    TO_NUMBER(CONFIDENCE)               AS CONFIDENCE
FROM STG_LAW_ADM
WHERE SIDO_NM = '서울특별시'
  AND LAW_CD IS NOT NULL
  AND ADM_CD IS NOT NULL;

COMMIT;


-- ═══════════════════════════════════════════════════════════════
-- STEP 3: 뷰 생성
-- ═══════════════════════════════════════════════════════════════

-- WFS emd_cd → 행정동 전체 (1:N)
CREATE OR REPLACE VIEW V_WFS_DONG_MAP AS
SELECT
    L.EMD_CD,
    L.GU_NM,
    L.LAW_NM,
    L.LAW_CD,
    M.ADM_CD,
    M.ADM_NM,
    M.CONFIDENCE
FROM LAW_DONG_SEOUL L
JOIN LAW_ADM_MAP M ON L.LAW_CD = M.LAW_CD;

-- WFS emd_cd → 행정동 단일값 (confidence 최고 우선, DAO 캐시용)
CREATE OR REPLACE VIEW V_LAW_TO_ADM AS
SELECT LAW_CD, EMD_CD, GU_NM, LAW_NM, ADM_CD, ADM_NM
FROM (
    SELECT L.LAW_CD, L.EMD_CD, L.GU_NM, L.LAW_NM,
           M.ADM_CD, M.ADM_NM,
           ROW_NUMBER() OVER (PARTITION BY L.EMD_CD ORDER BY M.CONFIDENCE DESC) AS RN
    FROM LAW_DONG_SEOUL L
    JOIN LAW_ADM_MAP M ON L.LAW_CD = M.LAW_CD
)
WHERE RN = 1;


-- ═══════════════════════════════════════════════════════════════
-- STEP 4: 검증 쿼리
-- ═══════════════════════════════════════════════════════════════
SELECT COUNT(*) FROM STG_LAW_ADM;          -- 2775 (전국)
SELECT COUNT(*) FROM LAW_DONG_SEOUL;       -- 180 (서울 법정동)
SELECT COUNT(*) FROM LAW_ADM_MAP;          -- 369 (서울 매핑)
SELECT * FROM V_LAW_TO_ADM WHERE ROWNUM<=5;

