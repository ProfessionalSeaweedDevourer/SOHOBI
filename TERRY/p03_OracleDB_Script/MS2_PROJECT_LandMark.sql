-- =====================================================
-- 한국관광공사 랜드마크 테이블
-- 콘텐츠타입: 12(관광지), 14(문화시설) - 고정값
-- 축제(15)는 백엔드 실시간 API 조회
-- =====================================================

DROP TABLE LANDMARK CASCADE CONSTRAINTS;

CREATE TABLE LANDMARK (
    CONTENT_ID      VARCHAR2(20)   PRIMARY KEY,
    CONTENT_TYPE_ID VARCHAR2(5),                  -- 12:관광지 14:문화시설
    TITLE           VARCHAR2(200),
    ADDR1           VARCHAR2(200),
    ADDR2           VARCHAR2(100),
    AREA_CODE       VARCHAR2(5),
    SIGUNGU_CODE    VARCHAR2(5),
    CAT1            VARCHAR2(10),
    CAT2            VARCHAR2(10),
    CAT3            VARCHAR2(10),
    MAP_X           NUMBER(15,7),
    MAP_Y           NUMBER(15,7),
    FIRST_IMAGE     VARCHAR2(500),
    FIRST_IMAGE2    VARCHAR2(500),
    TEL             VARCHAR2(100),
    HOMEPAGE        VARCHAR2(500),
    OVERVIEW        VARCHAR2(4000),
    LOAD_DT         DATE DEFAULT SYSDATE
);

CREATE INDEX IDX_LM_TYPE ON LANDMARK (CONTENT_TYPE_ID);
CREATE INDEX IDX_LM_XY   ON LANDMARK (MAP_X, MAP_Y);
CREATE INDEX IDX_LM_SGG  ON LANDMARK (SIGUNGU_CODE);

-- =====================================================
-- 학교 정보 테이블 (전국)
-- API 원본 컬럼 28개 + 좌표(MAP_X, MAP_Y) 추가
-- =====================================================

DROP TABLE SCHOOL_SEOUL CASCADE CONSTRAINTS;

CREATE TABLE SCHOOL_SEOUL (
    ATPT_OFCDC_SC_CODE      VARCHAR2(10),                -- 시도교육청코드
    ATPT_OFCDC_SC_NM        VARCHAR2(50),                -- 시도교육청명
    SD_SCHUL_CODE           VARCHAR2(20)  PRIMARY KEY,   -- 표준학교코드
    SCHUL_NM                VARCHAR2(100),               -- 학교명
    ENG_SCHUL_NM            VARCHAR2(200),               -- 영문학교명
    SCHUL_KND_SC_NM         VARCHAR2(30),                -- 학교종류명
    LCTN_SC_NM              VARCHAR2(30),                -- 소재지명
    JU_ORG_NM               VARCHAR2(100),               -- 관할조직명
    FOND_SC_NM              VARCHAR2(20),                -- 설립구분
    ORG_RDNZC               VARCHAR2(10),                -- 도로명우편번호
    ORG_RDNMA               VARCHAR2(300),               -- 도로명주소
    ORG_RDNDA               VARCHAR2(200),               -- 도로명상세주소
    ORG_TELNO               VARCHAR2(30),                -- 전화번호
    HMPG_ADRES              VARCHAR2(300),               -- 홈페이지주소
    COEDU_SC_NM             VARCHAR2(20),                -- 남녀공학구분명
    ORG_FAXNO               VARCHAR2(30),                -- 팩스번호
    HS_SC_NM                VARCHAR2(50),                -- 고등학교구분명
    INDST_SPECL_CCCCL_EXST_YN VARCHAR2(5),              -- 산업체특별학급존재여부
    HS_GNRL_BUSNS_SC_NM     VARCHAR2(50),                -- 고등학교일반실업구분명
    SPCLY_PURPS_HS_ORD_NM   VARCHAR2(100),               -- 특수목적고등학교계열명
    ENE_BFE_SEHF_SC_NM      VARCHAR2(50),                -- 입시전후기구분명
    DGHT_SC_NM              VARCHAR2(20),                -- 주야구분명
    FOND_YMD                VARCHAR2(10),                -- 설립일자
    FOAS_MEMRD              VARCHAR2(10),                -- 개교기념일
    DGHT_CRSE_SC_NM         VARCHAR2(30),                -- 주야과정
    ORD_SC_NM               VARCHAR2(50),                -- 계열명
    DDDEP_NM                VARCHAR2(100),               -- 학과명
    LOAD_DTM                VARCHAR2(20),                -- 적재일시(원본)
    MAP_X                   NUMBER(15,7),                -- 경도 (카카오 변환)
    MAP_Y                   NUMBER(15,7),                -- 위도 (카카오 변환)
    LOAD_DT                 DATE DEFAULT SYSDATE         -- DB 적재일시
);

CREATE INDEX IDX_SCH_KND  ON SCHOOL_SEOUL (SCHUL_KND_SC_NM);
CREATE INDEX IDX_SCH_LOC  ON SCHOOL_SEOUL (LCTN_SC_NM);
CREATE INDEX IDX_SCH_XY   ON SCHOOL_SEOUL (MAP_X, MAP_Y);

COMMIT;