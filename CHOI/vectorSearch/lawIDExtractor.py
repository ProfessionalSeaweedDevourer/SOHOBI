import os

import requests

# 사용자님의 오픈 API 인증키
API_KEY = os.getenv("LAW_API_KEY")

def fetch_law_ids(query="*", display=20):
    """
    법령 목록을 검색하여 법령명과 일련번호(ID)만 추출합니다.
    - query: 검색어 (기본값 '*'는 전체 검색)
    - display: 가져올 개수 (기본값 20개)
    """
    url = "https://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": API_KEY,
        "target": "law",
        "type": "JSON",
        "query": query,
        "display": display
    }
    
    print(f"법제처 API에서 '{query}' 검색어로 법령 목록을 가져옵니다...\n")
    response = requests.get(url, params=params)
    
    # 응답이 성공적인지 확인
    if response.status_code != 200:
        print(f"API 호출 실패 (상태 코드: {response.status_code})")
        return []

    data = response.json()
    law_list = data.get("LawSearch", {}).get("law", [])
    
    extracted_data = []
    
    # 필요한 정보만 쏙쏙 뽑아내기
    for law in law_list:
        law_info = {
            "법령명": law.get("법령명한글", ""),
            "법령일련번호": law.get("법령일련번호", ""), # 상세 조회에 필요한 핵심 ID (MST)
            "법령ID": law.get("법령ID", ""),
            "소관부처": law.get("소관부처명", "")
        }
        extracted_data.append(law_info)
        
    return extracted_data

if __name__ == "__main__":
    # 실행 시 20개의 법령 ID를 가져와서 출력합니다.
    # 원하는 검색어가 있다면 fetch_law_ids(query="식품위생법") 처럼 바꿀 수 있습니다.
    law_results = fetch_law_ids(query="위생관리법")
    
    print("=" * 50)
    print("총", len(law_results), "개의 법령 ID를 성공적으로 가져왔습니다.")
    print("=" * 50)
    
    for idx, law in enumerate(law_results, 1):
        print(f"[{idx}] {law['법령명']}")
        print(f"    ▶ 법령일련번호(MST) : {law['법령일련번호']}")
        print(f"    ▶ 법령ID           : {law['법령ID']}")
        print("-" * 50)