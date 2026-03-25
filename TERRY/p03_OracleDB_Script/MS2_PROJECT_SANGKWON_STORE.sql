-- 행정동별 상권 점포수, 개폐업 테이블

CREATE TABLE SANGKWON_STORE (
    BASE_YR_QTR_CD        VARCHAR2(6)    NOT NULL,  -- 기준_년분기_코드
    ADM_CD                VARCHAR2(10)   NOT NULL,  -- 행정동_코드
    ADM_NM                VARCHAR2(100),            -- 행정동_명
    SVC_INDUTY_CD         VARCHAR2(20)   NOT NULL,  -- 서비스_업종_코드
    SVC_INDUTY_NM         VARCHAR2(100),            -- 서비스_업종_명
    STOR_CO               NUMBER(10,1),             -- 업종_수
    SIMILR_INDUTY_STOR_CO NUMBER(10,1),             -- 유사업종_수
    OPBIZ_RT              NUMBER(10,1),             -- 개업률
    OPBIZ_STOR_CO         NUMBER(10,1),             -- 개업수량
    CLSBIZ_RT             NUMBER(10,1),             -- 폐업률
    CLSBIZ_STOR_CO        NUMBER(10,1),             -- 폐업수
    FRC_STOR_CO           NUMBER(10,1),             -- 프렌차이즈 수
    CONSTRAINT PK_SANGKWON_STORE PRIMARY KEY (BASE_YR_QTR_CD, ADM_CD, SVC_INDUTY_CD)
);