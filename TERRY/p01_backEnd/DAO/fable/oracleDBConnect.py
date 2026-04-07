# 위치: p01_backEnd/DAO/fable/oracleDBConnect.py
from oracledb import connect

DB_INFO = "shobi/8680@//10.1.92.119:1521/xe"

class OracleDBConnect:

    @staticmethod
    def makeConCur(info=None):
        con = connect(info or DB_INFO)
        cur = con.cursor()
        return con, cur

    @staticmethod
    def closeConCur(con, cur):
        cur.close()
        con.close()