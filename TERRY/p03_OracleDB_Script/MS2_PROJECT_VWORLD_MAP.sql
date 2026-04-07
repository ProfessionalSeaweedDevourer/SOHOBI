-1. 테이블 생성

-- 1) 소상공인_상권 먼저 생성 (템플릿용)
CREATE TABLE 소상공인_상권 (
    상가업소번호        VARCHAR2(20)   PRIMARY KEY,
    상호명             VARCHAR2(200),
    지점명             VARCHAR2(200),
    상권업종대분류코드  VARCHAR2(10),
    상권업종대분류명    VARCHAR2(100),
    상권업종중분류코드  VARCHAR2(10),
    상권업종중분류명    VARCHAR2(100),
    상권업종소분류코드  VARCHAR2(10),
    상권업종소분류명    VARCHAR2(200),
    표준산업분류코드    VARCHAR2(10),
    표준산업분류명      VARCHAR2(200),
    시도코드           VARCHAR2(10),
    시도명             VARCHAR2(50),
    시군구코드         VARCHAR2(10),
    시군구명           VARCHAR2(50),
    행정동코드         VARCHAR2(10),
    행정동명           VARCHAR2(100),
    법정동코드         VARCHAR2(10),
    법정동명           VARCHAR2(100),
    지번코드           VARCHAR2(20),
    대지구분코드        VARCHAR2(5),
    대지구분명         VARCHAR2(20),
    지번본번지         VARCHAR2(10),
    지번부번지         VARCHAR2(10),
    지번주소           VARCHAR2(300),
    도로명코드         VARCHAR2(20),
    도로명             VARCHAR2(200),
    건물본번지         VARCHAR2(10),
    건물부번지         VARCHAR2(10),
    건물관리번호        VARCHAR2(30),
    건물명             VARCHAR2(200),
    도로명주소         VARCHAR2(500),
    구우편번호         VARCHAR2(10),
    신우편번호         VARCHAR2(10),
    동정보             VARCHAR2(100),
    층정보             VARCHAR2(20),
    호정보             VARCHAR2(20),
    경도              NUMBER(15, 10),
    위도              NUMBER(15, 10)
);

-- 2. 시도별 테이블 생성 (소상공인_상권 구조 복사)
CREATE TABLE 소상공인_서울 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_경기 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_인천 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_부산 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_대구 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_광주 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_대전 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_울산 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_세종 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_강원 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_충북 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_충남 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_전북 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_전남 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_경북 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_경남 AS SELECT * FROM 소상공인_상권 WHERE 1=0;
CREATE TABLE 소상공인_제주 AS SELECT * FROM 소상공인_상권 WHERE 1=0;

-- 3. 소상공인_상권 삭제 (이제 필요없음)
DROP TABLE 소상공인_상권 CASCADE CONSTRAINTS PURGE;

-- 4. 인덱스 생성
CREATE INDEX IDX_서울_위경도 ON 소상공인_서울(위도, 경도);
CREATE INDEX IDX_서울_업종 ON 소상공인_서울(상권업종대분류명);
CREATE INDEX IDX_경기_위경도 ON 소상공인_경기(위도, 경도);
CREATE INDEX IDX_경기_업종 ON 소상공인_경기(상권업종대분류명);
CREATE INDEX IDX_인천_위경도 ON 소상공인_인천(위도, 경도);
CREATE INDEX IDX_인천_업종 ON 소상공인_인천(상권업종대분류명);
CREATE INDEX IDX_부산_위경도 ON 소상공인_부산(위도, 경도);
CREATE INDEX IDX_부산_업종 ON 소상공인_부산(상권업종대분류명);
CREATE INDEX IDX_대구_위경도 ON 소상공인_대구(위도, 경도);
CREATE INDEX IDX_대구_업종 ON 소상공인_대구(상권업종대분류명);
CREATE INDEX IDX_광주_위경도 ON 소상공인_광주(위도, 경도);
CREATE INDEX IDX_광주_업종 ON 소상공인_광주(상권업종대분류명);
CREATE INDEX IDX_대전_위경도 ON 소상공인_대전(위도, 경도);
CREATE INDEX IDX_대전_업종 ON 소상공인_대전(상권업종대분류명);
CREATE INDEX IDX_울산_위경도 ON 소상공인_울산(위도, 경도);
CREATE INDEX IDX_울산_업종 ON 소상공인_울산(상권업종대분류명);
CREATE INDEX IDX_세종_위경도 ON 소상공인_세종(위도, 경도);
CREATE INDEX IDX_세종_업종 ON 소상공인_세종(상권업종대분류명);
CREATE INDEX IDX_강원_위경도 ON 소상공인_강원(위도, 경도);
CREATE INDEX IDX_강원_업종 ON 소상공인_강원(상권업종대분류명);
CREATE INDEX IDX_충북_위경도 ON 소상공인_충북(위도, 경도);
CREATE INDEX IDX_충북_업종 ON 소상공인_충북(상권업종대분류명);
CREATE INDEX IDX_충남_위경도 ON 소상공인_충남(위도, 경도);
CREATE INDEX IDX_충남_업종 ON 소상공인_충남(상권업종대분류명);
CREATE INDEX IDX_전북_위경도 ON 소상공인_전북(위도, 경도);
CREATE INDEX IDX_전북_업종 ON 소상공인_전북(상권업종대분류명);
CREATE INDEX IDX_전남_위경도 ON 소상공인_전남(위도, 경도);
CREATE INDEX IDX_전남_업종 ON 소상공인_전남(상권업종대분류명);
CREATE INDEX IDX_경북_위경도 ON 소상공인_경북(위도, 경도);
CREATE INDEX IDX_경북_업종 ON 소상공인_경북(상권업종대분류명);
CREATE INDEX IDX_경남_위경도 ON 소상공인_경남(위도, 경도);
CREATE INDEX IDX_경남_업종 ON 소상공인_경남(상권업종대분류명);
CREATE INDEX IDX_제주_위경도 ON 소상공인_제주(위도, 경도);
CREATE INDEX IDX_제주_업종 ON 소상공인_제주(상권업종대분류명);

-- CHECK 제약조건 추가 (잘못된 시도 데이터 INSERT 방지)

ALTER TABLE 소상공인_서울 ADD CONSTRAINT chk_서울 CHECK (시도명 = '서울특별시');
ALTER TABLE 소상공인_경기 ADD CONSTRAINT chk_경기 CHECK (시도명 = '경기도');
ALTER TABLE 소상공인_인천 ADD CONSTRAINT chk_인천 CHECK (시도명 = '인천광역시');
ALTER TABLE 소상공인_부산 ADD CONSTRAINT chk_부산 CHECK (시도명 = '부산광역시');
ALTER TABLE 소상공인_대구 ADD CONSTRAINT chk_대구 CHECK (시도명 = '대구광역시');
ALTER TABLE 소상공인_광주 ADD CONSTRAINT chk_광주 CHECK (시도명 = '광주광역시');
ALTER TABLE 소상공인_대전 ADD CONSTRAINT chk_대전 CHECK (시도명 = '대전광역시');
ALTER TABLE 소상공인_울산 ADD CONSTRAINT chk_울산 CHECK (시도명 = '울산광역시');
ALTER TABLE 소상공인_세종 ADD CONSTRAINT chk_세종 CHECK (시도명 LIKE '세종%');
ALTER TABLE 소상공인_강원 ADD CONSTRAINT chk_강원 CHECK (시도명 LIKE '강원%');
ALTER TABLE 소상공인_충북 ADD CONSTRAINT chk_충북 CHECK (시도명 LIKE '충청북%');
ALTER TABLE 소상공인_충남 ADD CONSTRAINT chk_충남 CHECK (시도명 LIKE '충청남%');
ALTER TABLE 소상공인_전북 ADD CONSTRAINT chk_전북 CHECK (시도명 LIKE '전북%');
ALTER TABLE 소상공인_전남 ADD CONSTRAINT chk_전남 CHECK (시도명 LIKE '전라남%');
ALTER TABLE 소상공인_경북 ADD CONSTRAINT chk_경북 CHECK (시도명 LIKE '경상북%');
ALTER TABLE 소상공인_경남 ADD CONSTRAINT chk_경남 CHECK (시도명 LIKE '경상남%');
ALTER TABLE 소상공인_제주 ADD CONSTRAINT chk_제주 CHECK (시도명 LIKE '제주%');

-- 인덱스 전체 생성


SELECT 상호명, 도로명주소, 경도, 위도
FROM 소상공인_서울
WHERE 상호명 LIKE '%교촌%'
AND 시군구명 = '용산구' 





SELECT * FROM 소상공인_서울;
SELECT COUNT(*) FROM 소상공인_상권;




-- 1. 중복 상가업소번호 확인
SELECT 상가업소번호, COUNT(*) AS 건수
FROM 소상공인_상권
GROUP BY 상가업소번호
HAVING COUNT(*) > 1;

-- 2. 중복 건수 총합
SELECT COUNT(*) AS 중복건수
FROM (
    SELECT 상가업소번호
    FROM 소상공인_상권
    GROUP BY 상가업소번호
    HAVING COUNT(*) > 1
);

-- 3. 전체 건수 vs 유니크 건수 비교
SELECT 
    COUNT(*) AS 전체건수,
    COUNT(DISTINCT 상가업소번호) AS 유니크건수,
    COUNT(*) - COUNT(DISTINCT 상가업소번호) AS 중복건수
FROM 소상공인_상권;