import pdfkit
from jinja2 import Environment, FileSystemLoader

def generate_pdf():
    print("엔진 가동: 데이터를 HTML에 주입합니다...")

    # ─────────────────────────────────────────────
    # 1. 사용자 데이터
    #    ※ template.html의 {{ 변수명 }}과 키 이름이 반드시 일치해야 합니다.
    # ─────────────────────────────────────────────
    user_data = {
        # 신고인
        "owner_name":    "남대은",
        "owner_ssn":     "900101-*******",
        "owner_address": "서울특별시 강남구 테헤란로 123",
        "owner_phone":   "010-1234-5678",

        # 영업장
        "store_name":    "대박 떡볶이",
        "store_phone":   "02-987-6543",
        "store_address": "서울특별시 마포구 월드컵북로 1길 10",

        # 영업의 종류 (template의 {% if business_type == '...' %} 와 정확히 일치해야 함)
        "business_type": "일반음식점영업",

        # 면적 (숫자 문자열)
        "area_size":    "85.5",
        "area_outside": "",          # 외부 면적 없으면 빈 문자열

        # 식품용수 종류
        "water_type": "수돗물",

        # 공유주방 / 공동조리장 (True/False → Jinja2 {% if %} 조건에 사용)
        "shared_kitchen":      False,
        "shared_kitchen2":     False,
        "shared_kitchen2_info": "",

        # 신고 날짜  ← 기존 year/month/day에서 이름 변경
        "submit_year":  "2026",
        "submit_month": "03",
        "submit_day":   "09",
    }

    # ─────────────────────────────────────────────
    # 2. Jinja2 렌더링
    #    ※ render(**user_data) 로 dict를 언팩해야 변수가 주입됩니다.
    #      render(user_data) 로 쓰면 아무것도 치환되지 않습니다!
    # ─────────────────────────────────────────────
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    rendered_html = template.render(**user_data)   # ← ** 필수
    print("HTML 렌더링 완료. PDF 변환을 시작합니다...")

    # ─────────────────────────────────────────────
    # 3. wkhtmltopdf 경로 설정
    #    Windows 기본 설치 경로입니다. 다를 경우 수정하세요.
    # ─────────────────────────────────────────────
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

    try:
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    except Exception as e:
        print("\n[오류] wkhtmltopdf를 찾을 수 없습니다!")
        print("https://wkhtmltopdf.org/downloads.html 에서 Windows용을 설치하세요.")
        return

    # ─────────────────────────────────────────────
    # 4. PDF 변환 옵션
    #    - margin: 여백 0 (HTML 자체에서 padding으로 제어)
    #    - quiet: wkhtmltopdf 불필요한 경고 메시지 숨김
    # ─────────────────────────────────────────────
    options = {
        'page-size':             'A4',
        'orientation':           'Portrait',
        'encoding':              'UTF-8',
        'margin-top':            '0mm',
        'margin-right':          '0mm',
        'margin-bottom':         '0mm',
        'margin-left':           '0mm',
        'enable-local-file-access': None,
        'quiet':                 '',
    }

    # ─────────────────────────────────────────────
    # 5. PDF 생성
    # ─────────────────────────────────────────────
    output_filename = "food_business_report.pdf"

    try:
        pdfkit.from_string(
            rendered_html,
            output_filename,
            configuration=config,
            options=options
        )
        print(f"\n🎉 성공! [{output_filename}] 파일이 생성되었습니다.")
    except Exception as e:
        print(f"\n[오류] PDF 변환 중 문제가 발생했습니다: {e}")

if __name__ == "__main__":
    generate_pdf()