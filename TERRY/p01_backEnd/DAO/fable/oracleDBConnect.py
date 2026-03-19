# 위치: p01_backEnd/DAO/fable/oracleDBConnect.py
from oracledb import connect

DB_INFO = "fable/1@//10.100.0.172:1521/xe"

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