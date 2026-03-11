BizAgent AI: 1인 창업자용 행정 서류 자동화 시스템

BizAgent AI는 소상공인 및 예비 창업자가 직면하는 행정 서류 작성의 복잡성을 해결하기 위해 개발된 도메인 특화 에이전트(Domain-Specific Agent)입니다.

Microsoft Semantic Kernel 기반의 오케스트레이션 구조를 통해 사용자의 자연어 입력에서 필수 파라미터를 추출하며, 관공서 규격을 준수하는 Pixel-Perfect PDF 문서를 자동 생성합니다.

🌐 라이브 데모 (Live Demo)

본 서비스는 Azure App Service(Linux) 환경에 배포되어 있으며, 아래 링크를 통해 실시간으로 확인할 수 있습니다.

https://biz-helper-agent-2026-bxb8epbyejawfgck.koreacentral-01.azurewebsites.net/

(Azure 무료 티어 특성상 초기 접속 시 약 10~15초의 콜드 스타트 지연이 발생할 수 있습니다.)

✨ 핵심 기능 (Key Features)

상호작용형 정보 수집 (Interactive Slot Filling): 서류 생성에 필요한 필수 정보(상호명, 사업장 면적 등) 누락 시, AI가 대화를 통해 추가 정보를 식별하고 보완합니다.

관공서 규격 PDF 생성: 수집된 데이터를 바탕으로 PyPDF2 및 ReportLab을 활용하여 정규 서류 양식 위에 데이터를 정확히 매핑(Overlay)합니다.

확장 가능한 에이전트 아키텍처: FoodBusinessPlugin 등 모듈형 플러그인 구조를 채택하여 향후 정책 자금 추천, 상권 분석 등 타 도메인 에이전트와의 통합이 용이합니다.

🛠 기술 스택 (Tech Stack)

Backend & AI Orchestration

Language: Python 3.11

Framework: FastAPI

Orchestration: Microsoft Semantic Kernel

LLM: Azure OpenAI (GPT-4o)

Document Processing: PyPDF2, ReportLab

Frontend & Infrastructure

Frontend: HTML5, Tailwind CSS, Vanilla JavaScript

Cloud: Azure App Service (Linux)

🏗 시스템 아키텍처 (Architecture)

사용자 인터페이스(UI): Tailwind CSS 기반 웹 인터페이스를 통해 자연어 요청을 수신합니다.

백엔드 서버(API): FastAPI 비동기 엔드포인트를 통해 요청을 처리합니다.

AI 오케스트레이터: * ChatHistory를 통한 대화 맥락 유지

Auto Function Calling으로 서류 생성 의도 파악 및 해당 플러그인 트리거

플러그인 실행: overlay_main.py 모듈이 original.pdf 템플릿에 수집된 데이터를 병합하여 최종 결과물을 생성합니다.

📄 Use Case 명세서

상세한 기획 및 기능 정의는 아래 문서를 참조하십시오.

행정 에이전트 Use Case 명세서 (admin_agent_usecase.md)

💻 로컬 개발 환경 구성 (For Developers)

1. 환경 설정 및 패키지 설치

# 가상환경 구성
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt


2. 환경 변수 설정

app.py 내의 Azure OpenAI 관련 설정 값을 해당 리소스 정보로 수정해야 합니다.

AZURE_ENDPOINT = "YOUR_ENDPOINT"
AZURE_API_KEY = "YOUR_API_KEY"
AZURE_DEPLOYMENT_NAME = "gpt-4o"


3. 애플리케이션 실행

uvicorn app:app --reload


실행 후 http://127.0.0.1:8000에서 로컬 개발 테스트가 가능합니다.
