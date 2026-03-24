import json
import re
import os

# ============================================================
# 설정값
# ============================================================
MAX_CHUNK_LENGTH = 2000  # 이 글자수 초과 시 항(①②③...) 단위로 분할
INPUT_FILENAME = "law_data_for_embedding.json"
OUTPUT_FILENAME = "refined_law_data.json"


def clean_text(text):
    """불필요한 공백, HTML 태그, 개정이력 태그 정리"""
    if not text:
        return ""
    # HTML img 태그 제거 (법령 표 이미지 등)
    text = re.sub(r'<img[^>]*>', '[표/서식 이미지]', text)
    # 기타 HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 연속 공백/탭 정리 (줄바꿈은 보존 — 항 구분에 필요)
    text = re.sub(r'[^\S\n]+', ' ', text)
    # 연속 빈 줄 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_article_title(content):
    """조문에서 '제N조(제목)' 부분만 추출"""
    m = re.match(r'(제[\d조의]+\s*(?:\([^)]*\))?)', content)
    return m.group(1).strip() if m else ""


def split_by_paragraph(content, law_name, mst, article_no,
                        chapter_title, section_title,
                        metadata, base_index):
    """
    긴 조문을 항(①②③...) 단위로 분할.
    분할 후에도 MAX_CHUNK_LENGTH를 초과하면 그대로 둠 (추가 분할은 복잡도 대비 효과 낮음).
    """
    # 항 기호 패턴: ①②③... (원문에 나오는 패턴)
    paragraph_markers = re.split(r'(?=\n\s*[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])', content)

    # 항 분할이 안 되면 (마커 없거나 1개) 통째로 반환
    if len(paragraph_markers) <= 1:
        return None  # 분할 불가 → 호출부에서 통째로 처리

    article_title = extract_article_title(content)
    chunks = []

    for ci, chunk in enumerate(paragraph_markers):
        chunk = chunk.strip()
        if not chunk:
            continue

        # 청크 ID 생성
        chunk_id = "law_%s_%s_%s_p%s" % (mst, article_no, base_index, ci)
        chunk_id = re.sub(r'[^a-zA-Z0-9_-]', '_', chunk_id)

        cleaned = clean_text(chunk)

        # 분할된 청크에 조문 제목 맥락 추가
        if ci > 0 and article_title:
            context_prefix = "%s " % article_title
        else:
            context_prefix = ""

        hierarchy = build_hierarchy(law_name, chapter_title, section_title)
        full_text = "[%s] %s%s" % (hierarchy, context_prefix, cleaned)

        chunks.append({
            "id": chunk_id,
            "lawName": law_name,
            "mst": mst,
            "articleNo": article_no,
            "chapterTitle": chapter_title,
            "sectionTitle": section_title,
            "articleTitle": article_title,
            "content": cleaned,
            "fullText": full_text,
            "source": metadata.get("source", "국가법령정보센터"),
            "docType": metadata.get("type", "현행법령"),
            "chunkIndex": ci,
            "isChunked": True
        })

    return chunks


def build_hierarchy(law_name, chapter, section):
    """법령명 > 장 > 절 계층 문자열 생성"""
    parts = [law_name]
    if chapter:
        parts.append(chapter)
    if section:
        parts.append(section)
    return " > ".join(parts)


def is_chapter_header(content):
    """'제N장 ...' 패턴 판별"""
    return bool(re.match(r'^제\s*\d+\s*장\b', content))


def is_section_header(content):
    """'제N절 ...' 패턴 판별"""
    return bool(re.match(r'^제\s*\d+\s*절\b', content))


def is_article(content):
    """'제N조...' 실제 조문 판별"""
    return bool(re.match(r'^제\s*[\d]+', content)) and '조' in content[:15]


def preprocess_legal_data():
    """법령 데이터 전처리 메인 함수"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, INPUT_FILENAME)
    output_file = os.path.join(current_dir, OUTPUT_FILENAME)

    if not os.path.exists(input_file):
        print("❌ 파일을 찾을 수 없습니다: %s" % input_file)
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    refined_results = []
    current_chapter = ""
    current_section = ""
    prev_law_name = ""

    stats = {
        "total_input": len(data),
        "chapters_found": 0,
        "sections_found": 0,
        "articles_processed": 0,
        "chunks_created": 0,
        "skipped": 0,
    }

    for i, item in enumerate(data):
        content = item.get("content", "")
        law_name = item.get("law_name", "")
        metadata = item.get("metadata", {})

        # 법령이 바뀌면 장/절 초기화
        if law_name != prev_law_name:
            current_chapter = ""
            current_section = ""
            prev_law_name = law_name

        # --- 장 헤더 ---
        if is_chapter_header(content):
            current_chapter = clean_text(content)
            current_section = ""  # 장이 바뀌면 절 초기화
            stats["chapters_found"] += 1
            continue

        # --- 절 헤더 ---
        if is_section_header(content):
            current_section = clean_text(content)
            stats["sections_found"] += 1
            continue

        # --- 실제 조문만 처리 ---
        if not is_article(content):
            stats["skipped"] += 1
            continue

        mst = item.get("mst", "")
        article_no = item.get("article_no", "")
        cleaned_content = clean_text(content)
        article_title = extract_article_title(cleaned_content)

        # 긴 조문 분할 시도
        if len(cleaned_content) > MAX_CHUNK_LENGTH:
            chunks = split_by_paragraph(
                content, law_name, mst, article_no,
                current_chapter, current_section, metadata, i
            )
            if chunks:
                refined_results.extend(chunks)
                stats["chunks_created"] += len(chunks)
                stats["articles_processed"] += 1
                continue
            # 분할 실패 시 통째로 처리 (아래로 fall-through)

        # 일반 조문 (또는 분할 실패한 긴 조문)
        doc_id = "law_%s_%s_%s" % (mst, article_no, i)
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)

        hierarchy = build_hierarchy(law_name, current_chapter, current_section)
        full_text = "[%s] %s" % (hierarchy, cleaned_content)

        refined_item = {
            "id": doc_id,
            "lawName": law_name,
            "mst": mst,
            "articleNo": article_no,
            "chapterTitle": current_chapter,
            "sectionTitle": current_section,
            "articleTitle": article_title,
            "content": cleaned_content,
            "fullText": full_text,
            "source": metadata.get("source", "국가법령정보센터"),
            "docType": metadata.get("type", "현행법령"),
            "chunkIndex": 0,
            "isChunked": False
        }
        refined_results.append(refined_item)
        stats["articles_processed"] += 1

    # 결과 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(refined_results, f, ensure_ascii=False, indent=2)

    # 통계 출력
    print("=" * 60)
    print("✅ 법령 데이터 전처리 완료")
    print("=" * 60)
    print("  입력 항목 수       : %s개" % stats["total_input"])
    print("  장(章) 헤더        : %s개" % stats["chapters_found"])
    print("  절(節) 헤더        : %s개" % stats["sections_found"])
    print("  처리된 조문 수     : %s개" % stats["articles_processed"])
    print("  생성된 청크 수     : %s개 (긴 조문 분할)" % stats["chunks_created"])
    print("  건너뛴 항목        : %s개" % stats["skipped"])
    print("  최종 출력 문서 수  : %s개" % len(refined_results))
    print("  저장 위치          : %s" % output_file)
    print("=" * 60)

    # 출력 데이터 길이 분포
    lengths = [len(r["content"]) for r in refined_results]
    print("\n  content 길이 분포:")
    for lo, hi in [(0, 500), (500, 1000), (1000, 2000), (2000, 5000), (5000, 20000)]:
        cnt = sum(1 for l in lengths if lo <= l < hi)
        if cnt > 0:
            print("    %5s~%5s자: %s개" % (lo, hi, cnt))

    # 샘플 출력
    print("\n--- 출력 샘플 (첫 2개) ---")
    for r in refined_results[:2]:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print()


if __name__ == "__main__":
    preprocess_legal_data()