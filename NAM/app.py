from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
import os

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from BusinessPlugin import FoodBusinessPlugin

# ==========================================
# 🚨 대은님의 Azure Key 값을 여기에 다시 꼭 넣어주세요!
# ==========================================
AZURE_ENDPOINT = "https://agentpdf.services.ai.azure.com/"
AZURE_API_KEY = "여기에_키_값을_넣어주세요" 
AZURE_DEPLOYMENT_NAME = "gpt-4o"
# ==========================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 생성된 PDF를 다운로드할 수 있도록 폴더 열어주기
app.mount("/files", StaticFiles(directory="."), name="files")

class ChatMessage(BaseModel):
    message: str

kernel = Kernel()
chat_history = ChatHistory()
settings = None

@app.on_event("startup")
async def startup_event():
    global settings
    chat_service = AzureChatCompletion(
        deployment_name=AZURE_DEPLOYMENT_NAME, 
        endpoint=AZURE_ENDPOINT, 
        api_key=AZURE_API_KEY, 
        api_version="2024-12-01-preview"
    )
    kernel.add_service(chat_service)
    kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")
    settings = chat_service.get_prompt_execution_settings_class()(service_id="default")
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    system_prompt = """
    당신은 1인 창업가를 돕는 친절하고 전문적인 AI 행정 비서입니다. 
    사용자가 '식품 영업 신고서'를 만들고 싶어 하면, 아래의 필수 정보를 대화하듯 수집하세요.
    1. 대표자: 이름, 주민등록번호, 집 주소, 휴대전화 번호
    2. 영업소: 상호명, 매장 전화번호, 매장 주소, 영업 종류, 매장 면적
    모든 정보가 모이면 반드시 `BusinessDoc-create_food_report` 도구를 호출하세요.
    """
    chat_history.add_system_message(system_prompt)
    print("🚀 클라우드용 백엔드 가동 준비 완료!")

# 🌟 핵심 추가: 누군가 사이트 주소로 접속하면 index.html 웹 화면을 보여줌!
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.post("/api/chat")
async def chat_endpoint(req: ChatMessage):
    user_text = req.message
    chat_history.add_user_message(user_text)

    result = await kernel.get_service("default").get_chat_message_content(
        chat_history=chat_history,
        settings=settings,
        kernel=kernel
    )
    bot_reply = result.content
    chat_history.add_message(result)

    pdf_url = None
    if "✅ 서류 생성이 완료되었습니다" in bot_reply or ".pdf" in bot_reply:
        match = re.search(r"영업신고서_.*\.pdf", bot_reply)
        if match:
            filename = match.group(0)
            # 클라우드에서는 상대 경로로 다운로드 링크 제공
            pdf_url = f"/files/{filename}"

    return {
        "reply": bot_reply,
        "pdf_url": pdf_url
    }