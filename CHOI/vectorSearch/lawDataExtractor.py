import os
import requests
import xml.etree.ElementTree as ET
import json
import time
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 설정 읽기
API_KEY = os.getenv("LAW_API_KEY")
APP_ID = "default-app-id" # 필요 시 수정

# 법령 목록 (MST 번호 기반)
LAW_MST_LIST = [
    # {"name": "식품위생법", "mst": "277149"},
    # {"name": "식품위생법 시행령", "mst": "278067"},
    # {"name": "식품위생법 시행규칙", "mst": "282565"},
    # {"name": "상가건물 임대차보호법", "mst": "276285"},
    # {"name": "상가건물 임대차보호법 시행령", "mst": "280987"},
    # {"name": "근로기준법", "mst": "265959"},
    # {"name": "근로기준법 시행령", "mst": "270551"},
    # {"name": "근로기준법 시행규칙", "mst": "269393"},
    # {"name": "최저임금법", "mst": "218303"},
    # {"name": "최저임금법 시행령", "mst": "206564"},
    # {"name": "최저임금법 시행규칙", "mst": "282351"},
    # {"name": "부가가치세법", "mst": "276117"},
    # {"name": "부가가치세법 시행령", "mst": "283641"},
    # {"name": "부가가치세법 시행규칙", "mst": "282645"},
    # {"name": "소방시설 설치 및 관리에 관한 법률", "mst": "236977"},
    # {"name": "소방시설 설치 및 관리에 관한 법률 시행령", "mst": "279911"},
    # {"name": "소방시설 설치 및 관리에 관한 법률 시행규칙", "mst": "280195"},
    # {"name": "공중위생관리법", "mst": "259521"},
    # {"name": "공중위생관리법 시행령", "mst": "266301"},
    # {"name": "공중위생관리법 시행규칙", "mst": "283855"},
    # # --- 추가 법령 ---
    # {"name": "소득세법", "mst": "276127"},
    # {"name": "소득세법 시행령", "mst": "283631"},
    # {"name": "중소기업창업 지원법", "mst": "277133"},
    # {"name": "중소기업창업 지원법 시행령", "mst": "284871"},
    # {"name": "건축법", "mst": "273437"},
    # {"name": "건축법 시행령", "mst": "273503"},
    # {"name": "소상공인 보호 및 지원에 관한 법률", "mst": "277117"},
    # {"name": "국민건강증진법", "mst": "269929"},
    # {"name": "주세법", "mst": "267559"},
    # {"name": "폐기물관리법", "mst": "279797"},
    {"name": "개인정보 보호법", "mst": "270351"},
    {"name": "개인정보 보호법 시행령", "mst": "273745"},
]

def fetch_law_data(law_info):
    """국가법령정보센터 API를 통해 상세 조문을 수집합니다."""
    mst_id = law_info['mst']
    # 현행법령(target=law) 기준으로 요청 (이미지상 eflaw는 시행일자 필수이므로 law 권장)
    url = f"https://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=law&MST={mst_id}&type=XML"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
            
        root = ET.fromstring(response.content)
        
        # 에러 메시지 확인
        err_msg = root.findtext("message")
        if err_msg and ("실패" in err_msg or "제한" in err_msg):
            return None, f"API Error: {err_msg}"

        law_name = root.findtext(".//법령명한글") or law_info['name']
        articles = []
        
        # 조문 단위 데이터 추출
        article_nodes = root.findall(".//조문단위")
        if not article_nodes:
            return None, "No articles found (Check MST or API Key)"

        for item in article_nodes:
            # 조문 번호 및 가지번호 처리
            article_no = item.findtext("조문번호", "")
            article_content = item.findtext("조문내용", "").replace("\n", " ").strip()
            
            if not article_content:
                continue

            # 항/호/목 등 세부 내용 병합
            sub_contents = []
            for hang in item.findall(".//항"):
                h_text = hang.findtext("항내용", "").strip()
                if h_text: sub_contents.append(h_text)
                for ho in hang.findall(".//호"):
                    ho_text = ho.findtext("호내용", "").strip()
                    if ho_text: sub_contents.append(f"  {ho_text}")

            full_body = article_content + ("\n" + "\n".join(sub_contents) if sub_contents else "")
            
            articles.append({
                "law_name": law_name,
                "mst": mst_id,
                "article_no": article_no,
                "content": full_body,
                "metadata": {
                    "source": "국가법령정보센터",
                    "type": "현행법령"
                }
            })
            
        return articles, None
    except Exception as e:
        return None, str(e)

def save_to_json(data, filename="law_data_for_embedding.json"):
    """수집된 데이터를 JSON 파일로 저장합니다."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"\n[성공] 총 {len(data)}개의 조문이 {filename}에 저장되었습니다.")

if __name__ == "__main__":
    if not API_KEY:
        print("에러: .env 파일에 LAW_API_KEY가 설정되지 않았습니다.")
    else:
        all_data = []
        print(f"=== 수집 시작 (ID: {API_KEY}) ===")
        
        for law in LAW_MST_LIST:
            print(f"처리 중: {law['name']} (MST: {law['mst']})...", end=" ", flush=True)
            results, err = fetch_law_data(law)
            
            if results:
                all_data.extend(results)
                print(f"성공 ({len(results)}개 조문)")
            else:
                print(f"실패 ({err})")
            
            time.sleep(0.2) # API 서버 부하 방지
            
        if all_data:
            save_to_json(all_data)
        else:
            print("수집된 데이터가 없어 파일을 저장하지 않았습니다.")