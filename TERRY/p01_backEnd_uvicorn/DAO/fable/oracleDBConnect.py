# AOP적인 생각: 어떤DB작업을 하던지 공통된 부분이 존재
#   -> 따로 정리해야겠다
# 그정리하는 거는 이번 프로젝트 뿐만아니라, 앞으로 계속 사용할듯
# db관련 라이브러리를 만들어야겠다

import oracledb


class OracleDBConnect:
    def makeConCur(info, timeout: int = 60):
        """
        Oracle DB 커넥션 생성
        timeout: 쿼리 대기 최대 시간(초), 기본 60초
        대용량 테이블(경기 등) 조회 시 더 큰 값 전달 가능
        """
        con = oracledb.connect(info)
        con.call_timeout = timeout * 1000  # ms 단위
        cur = con.cursor()
        return con, cur

    def makeConCurLarge(info):
        """대용량 테이블 전용 - 타임아웃 10분"""
        return OracleDBConnect.makeConCur(info, timeout=600)

    def closeConCur(con, cur):
        cur.close()
        con.close()
