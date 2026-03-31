import pandas as pd
import oracledb
import os

# DB 접속 정보 (README 기준)
db_config = {
    "user": "shobi",
    "password": "8680",
    "host": "10.1.92.119",
    "port": 1521,
    "service_name": "xe",
}

# 요청하신 상대 경로 설정
csv_file_path = "./p04_DataLoader/csv/sdot_sensor/서울시 도시데이터 센서(S-DoT) 유동인구 설치 위치정보.csv"


def insert_sdot_data():
    conn = None
    try:
        # Thin 모드 연결 (Python 3.9/3.12 공통)
        conn = oracledb.connect(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            service_name=db_config["service_name"],
        )
        cursor = conn.cursor()

        if not os.path.exists(csv_file_path):
            print(f"❌ 파일을 찾을 수 없습니다: {os.path.abspath(csv_file_path)}")
            return

        # CSV 로드 (euc-kr)
        try:
            df = pd.read_csv(csv_file_path, encoding="euc-kr")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file_path, encoding="cp949")

        # 컬럼 순서에 따라 강제 매핑 (이름 인식 오류 방지)
        df.columns = ["SEQ", "SENSOR_CD", "SERIAL_NO", "ADDR", "LAT", "LNG"]

        # 데이터 정제 (숫자 변환 및 결측치 처리)
        df["SEQ"] = pd.to_numeric(df["SEQ"], errors="coerce").fillna(0).astype(int)
        df["SENSOR_CD"] = (
            pd.to_numeric(df["SENSOR_CD"], errors="coerce").fillna(0).astype(int)
        )
        df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce").fillna(0.0)
        df["LNG"] = pd.to_numeric(df["LNG"], errors="coerce").fillna(0.0)

        # SQL 실행 (반드시 DB의 컬럼명과 일치해야 함)
        insert_sql = """
            INSERT INTO SDOT_SENSOR (SEQ, SENSOR_CD, SERIAL_NO, ADDR, LAT, LNG)
            VALUES (:1, :2, :3, :4, :5, :6)
        """

        data_rows = []
        for _, row in df.iterrows():
            # 헤더 중복 방지
            if _ == 0 and row["SEQ"] == 0:
                continue

            data_rows.append(
                (
                    int(row["SEQ"]),
                    int(row["SENSOR_CD"]),
                    str(row["SERIAL_NO"]).strip()[:50],
                    str(row["ADDR"]).strip()[:500],
                    float(row["LAT"]),
                    float(row["LNG"]),
                )
            )

        # 기존 데이터 삭제 후 고속 삽입
        cursor.execute("DELETE FROM SDOT_SENSOR")
        cursor.executemany(insert_sql, data_rows)

        conn.commit()
        print(f"✅ 적재 성공: 총 {len(data_rows)}건의 S-DoT 데이터가 입력되었습니다.")

    except Exception as e:
        print(f"❌ 오류 상세: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    insert_sdot_data()
