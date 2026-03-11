import requests
import json

# 터미널에서 받은 localhost 주소를 여기에 넣으세요! (포트 번호 7071 등 확인)
api_url = "https://founderhelper-caaabnaqgnbrb4gh.koreacentral-01.azurewebsites.net/api/createbizdoc"

# 에이전트가 수집했다고 가정한 사장님의 JSON 데이터
test_data = {
    "owner_name": "김철수",
    "owner_ssn": "900101-*******",
    "owner_address": "서울특별시 강남구 테헤란로 123",
    "owner_phone": "010-1234-5678",
    "store_name": "대박 떡볶이",
    "store_phone": "02-987-6543",
    "store_address": "서울특별시 마포구 월드컵북로 1길 10",
    "business_type": "일반음식점영업",
    "area_size": "85.5",
    "submit_year": "2026",
    "submit_month": "03",
    "submit_day": "09"
}

print("API로 데이터를 전송합니다...")

# POST 방식으로 JSON 데이터 쏘기
response = requests.post(api_url, json=test_data)

# 결과 확인
if response.status_code == 200:
    print("\n✅ 성공! 반환된 데이터:")
    print(response.json()) # 여기에 Azure Storage 다운로드 링크가 떠야 합니다!
else:
    print(f"\n❌ 에러 발생 (상태 코드 {response.status_code}):")
    print(response.text)