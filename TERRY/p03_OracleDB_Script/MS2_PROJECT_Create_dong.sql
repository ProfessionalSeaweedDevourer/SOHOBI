-- ═══════════════════════════════════════════════════════════════
-- STEP 1: 스테이징 테이블 생성 (CSV 컬럼 그대로)
-- DBeaver에서 law_admin_mapping.csv → 이 테이블로 import
-- ═══════════════════════════════════════════════════════════════
DROP TABLE LAW_ADM_MAP;

CREATE TABLE LAW_ADM_MAP (
    EMD_CD      VARCHAR2(10),
    LAW_CD      VARCHAR2(10),
    GU_NM       VARCHAR2(50),
    LAW_NM      VARCHAR2(100),
    ADM_CD      VARCHAR2(15),
    ADM_NM      VARCHAR2(100),
    CONFIDENCE  VARCHAR2(10),
    CONSTRAINT PK_LAW_ADM_MAP PRIMARY KEY (LAW_CD)
   
);

-- ═══════════════════════════════════════════════════════════════
-- STEP 2: CSV import 후 실행 - 메인 테이블 생성 및 데이터 이관
-- ═══════════════════════════════════════════════════════════════

-- 2-1. 법정동 마스터 (서울만, 중복제거)
DROP TABLE LAW_DONG_SEOUL;

CREATE TABLE LAW_DONG_SEOUL (
    LAW_CD  VARCHAR2(10) PRIMARY KEY,
    EMD_CD  VARCHAR2(10),
    GU_NM   VARCHAR2(50),
    LAW_NM  VARCHAR2(100)
);