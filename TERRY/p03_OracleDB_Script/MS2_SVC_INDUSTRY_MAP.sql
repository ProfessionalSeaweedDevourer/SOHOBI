-- 소상공인_서울 업종코드 매핑 테이블 생성 및 INSERT
-- 실행: DBeaver에서 Oracle DB에 직접 실행
DROP TABLE SVC_INDUTY_MAP CASCADE CONSTRAINTS;
-- 1. 매핑 테이블 생성
CREATE TABLE SVC_INDUTY_MAP (
    SVC_INDUTY_CD  VARCHAR2(20)  PRIMARY KEY,  -- CS100001 등
    SVC_INDUTY_NM  VARCHAR2(100),              -- 한식음식점 등
    SVC_CD         VARCHAR2(10),               -- I2, G2 등
    SVC_NM         VARCHAR2(100)               -- 음식점업 등
);


-- 2. 확인
SELECT SVC_CD, SVC_NM, COUNT(*) AS 업종수
FROM SVC_INDUTY_MAP
GROUP BY SVC_CD, SVC_NM
ORDER BY SVC_CD;