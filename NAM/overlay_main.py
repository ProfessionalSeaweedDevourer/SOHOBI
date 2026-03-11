"""
식품 영업 신고서 - PDF 오버레이 생성기 (Pixel-Perfect)
=======================================================
원본 PDF(original.pdf) 위에 투명 레이어를 얹어 텍스트를 
정확한 위치에 삽입합니다.

좌표 추출 방법:
  - pdfplumber로 원본 PDF의 텍스트·테이블 선 좌표 추출
  - 수평/수직 선 데이터로 셀 경계 특정
  - reportlab y = PAGE_H(841) - pdfplumber_top - text_height
  - 행 베이스라인 = (셀_상단_y + 셀_하단_y) / 2 - font_size * 0.3

검증된 좌표 (A4 595×841pt 기준, reportlab bottom-left 원점):
  - owner_name    : (321.0, 696.4)
  - owner_ssn     : (420.3, 696.4)
  - owner_address : (321.0, 678.3)
  - owner_phone   : (367.9, 678.3)
  - store_name    : (167.0, 654.9)
  - store_phone   : (367.9, 654.9)
  - area_size     : (270.0, 535.7)  ← [ 숫자 ㎡] 안쪽
  - area_outside  : (384.2, 535.7)
  - store_address : (198.2, 524.8)
"""

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

# ─────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────
PAGE_H = 841  # A4 높이 (points)

# 수직선·수평선 분석으로 확정된 셀 경계 x 좌표
#   x=57.3  : 좌측 테두리
#   x=113.0 : 신고인/신고사항 세로라벨 | 내용 경계
#   x=317.0 : 성명·주소 셀 우측 경계 (= 주민번호라벨 시작)
#   x=416.3 : 주민번호라벨 우측 경계 (= 주민번호 값 시작)
#   x=538.0 : 우측 테두리
#
# 수평선으로 확정된 신고인 섹션 행 y 범위 (reportlab 기준)
#   성명 행 : y_bottom=708.1, y_top=690.1  →  baseline=696.4
#   주소 행 : y_bottom=690.1, y_top=672.0  →  baseline=678.3
#   명칭 행 : y_bottom=665.3, y_top=650.0  →  baseline=654.9

def row_baseline(y_bot: float, y_top: float, font_size: float = 9.0) -> float:
    """셀 수평선 y값(reportlab)으로 텍스트 베이스라인 계산"""
    return (y_bot + y_top) / 2 - font_size * 0.3

def top2rl(pdfplumber_top: float, text_h: float = 8.0) -> float:
    """pdfplumber top → reportlab y"""
    return PAGE_H - pdfplumber_top - text_h


# ─────────────────────────────────────────────────────────────
# 입력 필드 좌표 (x, y) — reportlab bottom-left 기준
# ─────────────────────────────────────────────────────────────
FIELD_COORDS = {
    # ── 신고인 ──────────────────────────────────────────────
    # 성명 셀: x=317~538, 값 시작 x=321 (경계+4)
    "owner_name":    (321.0,  row_baseline(708.1, 690.1)),

    # 주민등록번호 셀: x=416.3~538, 값 시작 x=420.3
    "owner_ssn":     (420.3,  row_baseline(708.1, 690.1)),

    # 주소 셀: x=317~538 중 317~416 (주소), 값 시작 x=321
    "owner_address": (321.0,  row_baseline(690.1, 672.0)),

    # 전화번호(신고인) 셀: x=416.3~538, 값 시작 x=420.3
    # 라벨 "전화번호" x0=319.9, x1=359.9 → 값은 363.9 이후
    # 수직선 x=416.3이 실제 셀 경계 → 값: x=420.3
    "owner_phone":   (420.3,  row_baseline(690.1, 672.0)),

    # ── 영업장 ──────────────────────────────────────────────
    # 명칭(상호) 셀: 라벨 끝 x1=163.3 → 값 x=167.3
    "store_name":    (167.3,  row_baseline(665.3, 650.0)),

    # 전화번호(영업장): 라벨 끝 x1=359.9 → 값 x=363.9
    "store_phone":   (363.9,  row_baseline(665.3, 650.0)),

    # ── 영업장 면적 ─────────────────────────────────────────
    # 내부: "[ __ ㎡]" 에서 [ x=264.2 → 숫자 x=270.0
    "area_size":     (270.0,  top2rl(297.3)),

    # 외부: 두 번째 "[ __ ㎡]" [ x=379.2 → 숫자 x=384.2
    "area_outside":  (384.2,  top2rl(297.3)),

    # ── 영업장 소재지 ────────────────────────────────────────
    # "소재지:" 라벨 끝 x1=194.2 → 값 x=198.2
    "store_address": (198.2,  top2rl(308.2)),

    # ── 신고 날짜 ────────────────────────────────────────────
    # "년" x=442.8  "월" x=483.1  "일" x=523.6  (pdfplumber top=511.0)
    "submit_year":   (406.0,  top2rl(511.0)),
    "submit_month":  (451.0,  top2rl(511.0)),
    "submit_day":    (493.0,  top2rl(511.0)),
}


# ─────────────────────────────────────────────────────────────
# 영업의 종류 체크박스 좌표
# bracket "[" 의 x 좌표 (pdfplumber), 해당 행의 top 좌표
# √ 는 bracket x + 5 위치에 찍힘
# ─────────────────────────────────────────────────────────────
BIZ_TYPE_COORDS = {
    "즉석판매제조·가공업":   (161.4, 195.3),
    "집단급식소 식품판매업": (289.7, 195.3),
    "일반음식점영업":        (423.2, 195.3),
    "식품운반업":            (161.4, 212.4),
    "기타식품판매업":        (289.7, 212.4),
    "위탁급식영업":          (423.2, 212.4),
    "식품소분업":            (161.4, 229.4),
    "식품냉동·냉장업":       (289.7, 229.4),
    "제과점영업":            (423.2, 229.4),
    "식용얼음판매업":        (161.4, 246.4),
    "용기·포장지제조업":     (289.7, 246.4),
    "식품자동판매기영업":    (161.4, 263.6),
    "옹기류제조업":          (289.7, 263.6),
    "유통전문판매업":        (161.4, 280.6),
    "휴게음식점영업":        (289.7, 280.6),
}


# ─────────────────────────────────────────────────────────────
# 폰트 후보 경로 (OS별 자동 감지)
# ─────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    ("MalgunGothic",  r"C:/Windows/Fonts/malgun.ttf"),
    ("MalgunGothic",  r"C:/Windows/Fonts/Malgun.ttf"),
    ("NanumGothic",   "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    ("AppleGothic",   "/System/Library/Fonts/AppleGothic.ttf"),
    ("AppleSDGothic", "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
]


# ─────────────────────────────────────────────────────────────
def _load_korean_font() -> str:
    """사용 가능한 한글 폰트를 찾아 등록 후 이름 반환"""
    for name, path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                print(f"  ✅ 폰트: {name}  ({path})")
                return name
            except Exception as e:
                print(f"  ⚠️  폰트 등록 실패 ({path}): {e}")
    print("  ⚠️  한글 폰트 없음 → Helvetica 사용 (한글 깨질 수 있음)")
    return "Helvetica"


def create_overlay(data: dict) -> io.BytesIO:
    """
    투명 PDF 오버레이 생성.
    data 딕셔너리의 키는 FIELD_COORDS의 키와 일치해야 합니다.
    """
    packet   = io.BytesIO()
    c        = canvas.Canvas(packet, pagesize=A4)
    font_name = _load_korean_font()

    c.setFillColorRGB(0, 0, 0)

    # ── 헬퍼 ──────────────────────────────────────────────────
    def put(field: str, text: str, font_size: float = 9.0):
        """필드 키로 좌표를 찾아 텍스트 출력"""
        if not text or field not in FIELD_COORDS:
            return
        x, y = FIELD_COORDS[field]
        c.setFont(font_name, font_size)
        c.drawString(x, y, text)

    # ── 신고인 ────────────────────────────────────────────────
    put("owner_name",    data.get("owner_name", ""))
    put("owner_ssn",     data.get("owner_ssn",  ""))

    # 주소가 길 경우 폰트 크기를 줄여 셀 내에 맞춤
    addr = data.get("owner_address", "")
    put("owner_address", addr, font_size=8.5 if len(addr) > 18 else 9.0)

    put("owner_phone",   data.get("owner_phone", ""))

    # ── 영업장 ────────────────────────────────────────────────
    put("store_name",  data.get("store_name",  ""))
    put("store_phone", data.get("store_phone", ""))

    # ── 영업의 종류 체크 ─────────────────────────────────────
    biz = data.get("business_type", "")
    if biz in BIZ_TYPE_COORDS:
        bx, bt = BIZ_TYPE_COORDS[biz]
        c.setFont(font_name, 9)
        c.drawString(bx + 5, top2rl(bt), "√")
    elif biz:
        print(f"  ⚠️  업종 '{biz}' 이(가) BIZ_TYPE_COORDS에 없습니다.")
        print(f"      사용 가능한 업종: {list(BIZ_TYPE_COORDS.keys())}")

    # ── 면적 ──────────────────────────────────────────────────
    put("area_size",    data.get("area_size",    ""))
    put("area_outside", data.get("area_outside", ""))

    # ── 소재지 ────────────────────────────────────────────────
    saddr = data.get("store_address", "")
    put("store_address", saddr, font_size=8.5 if len(saddr) > 22 else 9.0)

    # ── 날짜 ──────────────────────────────────────────────────
    put("submit_year",  data.get("submit_year",  ""))
    put("submit_month", data.get("submit_month", ""))
    put("submit_day",   data.get("submit_day",   ""))

    c.save()
    packet.seek(0)
    return packet


def merge_pdf(original_pdf_path: str, output_path: str, data: dict):
    """
    원본 PDF에 오버레이를 병합하여 output_path에 저장합니다.

    Args:
        original_pdf_path: 원본 관공서 양식 PDF 경로
        output_path:       결과 PDF 저장 경로
        data:              입력 데이터 딕셔너리
    """
    if not os.path.exists(original_pdf_path):
        print(f"[오류] 원본 PDF 없음: '{original_pdf_path}'")
        return

    print(f"원본 PDF 로드: {original_pdf_path}")
    existing_pdf = PdfReader(open(original_pdf_path, "rb"))
    output       = PdfWriter()

    # 1페이지 오버레이 생성 및 병합
    print("오버레이 생성 중...")
    overlay_packet = create_overlay(data)
    overlay_pdf    = PdfReader(overlay_packet)

    page = existing_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    output.add_page(page)

    # 나머지 페이지(뒤쪽) 그대로 추가
    for i in range(1, len(existing_pdf.pages)):
        output.add_page(existing_pdf.pages[i])

    with open(output_path, "wb") as f:
        output.write(f)

    print(f"\n🎉 완료 → [{output_path}]")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    user_data = {
        # ── 신고인 ──────────────────────────────────────────
        "owner_name":    "남대은",
        "owner_ssn":     "900101-*******",
        "owner_address": "서울특별시 강남구 테헤란로 123",
        "owner_phone":   "010-1234-5678",

        # ── 영업장 ──────────────────────────────────────────
        "store_name":    "대박 떡볶이",
        "store_phone":   "02-987-6543",
        "store_address": "서울특별시 마포구 월드컵북로 1길 10",

        # ── 영업의 종류 ──────────────────────────────────────
        # BIZ_TYPE_COORDS의 키와 정확히 일치해야 합니다.
        "business_type": "일반음식점영업",

        # ── 면적 (숫자만, ㎡ 기호는 원본에 이미 있음) ────────
        "area_size":    "85.5",
        "area_outside": "",          # 외부 면적 없으면 빈 문자열

        # ── 신고 날짜 ────────────────────────────────────────
        "submit_year":  "2026",
        "submit_month": "03",
        "submit_day":   "09",
    }

    merge_pdf(
        original_pdf_path="original.pdf",   # 원본 관공서 양식 PDF
        output_path="result.pdf",
        data=user_data,
    )

    