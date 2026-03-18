import json
import re
import os

def clean_text(text):
    """불필요한 공백 및 줄바꿈 정리"""
    if not text:
        return ""
    # 연속된 공백을 하나로, 앞뒤 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_legal_data():
    """
    CHOI/vectorSearch/ 폴더 내의 법령 데이터를 정제합니다.
    """
    # 현재 스크립트의 경로를 기준으로 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, "law_data_for_embedding.json")
    output_file = os.path.join(current_dir, "refined_law_data.json")

    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        refined_results = []
        current_chapter = "총칙" # 초기 장 제목 기본값

        for i, item in enumerate(data):
            content = item.get("content", "")
            
            # 1. '제N장'으로 시작하는 경우 -> 현재 장 제목 업데이트
            chapter_match = re.match(r'^제\s*\d+\s*장\s+([^0-9(]+)', content)
            if chapter_match:
                current_chapter = chapter_match.group(0).strip()
                continue
            
            # 2. '제N조'로 시작하는 실제 조문 처리
            if content.startswith("제") and "조" in content[:10]:
                law_name = item.get("law_name", "")
                mst = item.get("mst", "")
                article_no = item.get("article_no", "")
                
                cleaned_content = clean_text(content)
                
                # RAG 효율을 위한 통합 검색용 텍스트
                full_text = f"[{law_name}] {current_chapter} - {cleaned_content}"
                
                # Azure AI Search ID 규칙 (영문, 숫자, 대시, 언더바만 가능)
                # 안전하게 인덱스 번호를 포함한 ID 생성
                doc_id = f"law_{mst}_{article_no}_{i}"
                doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)

                refined_item = {
                    "id": doc_id,
                    "lawName": law_name,
                    "mst": mst,
                    "articleNo": article_no,
                    "chapterTitle": current_chapter,
                    "content": cleaned_content,
                    "fullText": full_text,
                    "metadata": {
                        "source": item.get("metadata", {}).get("source", "국가법령정보센터"),
                        "type": item.get("metadata", {}).get("type", "현행법령")
                    }
                }
                refined_results.append(refined_item)

        # 결과 파일 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(refined_results, f, ensure_ascii=False, indent=4)

        print(f"✅ 정제 프로세스 완료!")
        print(f"   - 처리된 조문 수: {len(refined_results)}개")
        print(f"   - 저장 위치: {output_file}")

    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    preprocess_legal_data()