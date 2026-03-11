from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import re

# 시맨틱 커널 관련 임포트 (기존 agent.py와 동일)
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory

# 대은님의 로컬용 플러그인 임포트
from BusinessPlugin import FoodBusinessPlugin

# ==========================================
# 🚨 Azure 키 설정 (반드시 본인 키로 수정하세요)
# ==========================================
AZURE_ENDPOINT = "https://agentpdf.services.ai.azure.com/"
AZURE_API_KEY = "여기에_키_값을_넣어주세요" 
AZURE_DEPLOYMENT_NAME = "gpt-4o"
# ==========================================

# FastAPI 앱 생성
app = FastAPI()

# 웹사이트(HTML)에서 API를 호출할 수 있도록 CORS 허용 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 생성된 PDF 파일을 웹에서 다운로드할 수 있도록 정적 파일 폴더 마운트 (현재 폴더를 통째로 제공)
app.mount("/files", StaticFiles(directory="."), name="files")

# 프론트엔드에서 날아올 데이터 형식 정의
class ChatMessage(BaseModel):
    message: str

# 글로벌 AI 상태 보관용
kernel = Kernel()
chat_history = ChatHistory()
settings = None

@app.on_event("startup")
async def startup_event():
    global settings
    # AI 뇌(Azure) 장착
    chat_service = AzureChatCompletion(
        deployment_name=AZURE_DEPLOYMENT_NAME, 
        endpoint=AZURE_ENDPOINT, 
        api_key=AZURE_API_KEY, 
        api_version="2024-12-01-preview"
    )
    kernel.add_service(chat_service)
    
    # PDF 자판기 장착
    kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")
    settings = chat_service.get_prompt_execution_settings_class()(service_id="default")
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # 에이전트 교육 (시스템 프롬프트)
    system_prompt = """
    당신은 1인 창업가를 돕는 친절하고 전문적인 AI 행정 비서입니다. 
    사용자가 '식품 영업 신고서'를 만들고 싶어 하면, 아래의 필수 정보를 대화하듯 수집하세요.
    1. 대표자: 이름, 주민등록번호, 집 주소, 휴대전화 번호
    2. 영업소: 상호명, 매장 전화번호, 매장 주소, 영업 종류, 매장 면적
    모든 정보가 모이면 반드시 `BusinessDoc-create_food_report` 도구를 호출하세요.
    """
    chat_history.add_system_message(system_prompt)
    print("🚀 FastAPI 백엔드 & AI 에이전트 가동 완료!")

# 핵심: 프론트엔드가 채팅을 보내면 처리하는 주소
@app.post("/api/chat")
async def chat_endpoint(req: ChatMessage):
    user_text = req.message
    chat_history.add_user_message(user_text)

    # AI에게 답변 받아오기 (PDF 생성 포함)
    result = await kernel.get_service("default").get_chat_message_content(
        chat_history=chat_history,
        settings=settings,
        kernel=kernel
    )
    bot_reply = result.content
    chat_history.add_message(result)

    # 💡 PDF 생성 감지 로직
    # BusinessPlugin이 반환한 문자열에서 파일명("영업신고서_***.pdf")을 추출
    pdf_url = None
    if "✅ 서류 생성이 완료되었습니다" in bot_reply or ".pdf" in bot_reply:
        match = re.search(r"영업신고서_.*\.pdf", bot_reply)
        if match:
            filename = match.group(0)
            # 프론트엔드가 다운로드할 수 있는 웹 경로 생성 (/files/... )
            pdf_url = f"http://localhost:8000/files/{filename}"

    return {
        "reply": bot_reply,
        "pdf_url": pdf_url
    }