from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
import os
from dotenv import load_dotenv

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from BusinessPlugin import FoodBusinessPlugin
from GovSupportPlugin import GovSupportPlugin

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../sohobi-azure/.env"))

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

SYSTEM_PROMPT = """너는 "SOHOBI"라는 서비스의 AI 비서야. F&B(카페/식당/베이커리) 창업자만 돕는다.

[네가 할 수 있는 것 - 이것만 해]
1. 정부지원사업 검색: 사용자 업종/지역에 맞는 지원사업을 검색 도구로 찾아서 안내
2. 영업신고서 작성: 사용자 정보 받아서 PDF 생성

[절대 하면 안 되는 것]
- 위 두 가지 외에는 어떤 정보도 제공하지 마. 시장동향, 상권분석, 메뉴추천, 인테리어, 마케팅, 일반상식, 정치, 경제, 외국 정보 등 일절 답하지 마.
- 사용자가 범위 밖 질문을 하면 이렇게만 답해: "저는 정부지원사업 검색과 영업신고서 작성만 도와드릴 수 있어요. 이 중에 궁금한 게 있으신가요?"
- 절대 "~에 대해 안내해드릴 수 있습니다", "~도 가능합니다" 식으로 능력을 부풀리지 마.

[말투]
- 자연스럽게 대화해. 번호/목록/제목(###)/볼드(**)/구분선(---)/이모지 금지.
- 일상 대화는 짧게 2~3문장.
- 지원사업 안내할 때는 필요한 만큼 충분히 설명해도 돼. 다만 나열하지 말고 자연스러운 문장으로.

[예시 - 일상 대화]
사용자: 넌 뭐 할 수 있어?
너: 정부지원사업 찾아드리고, 영업신고서 작성 도와드려요. 뭐가 궁금하세요?

사용자: 중국 시장 동향 알려줘
너: 저는 정부지원사업 검색과 영업신고서 작성만 도와드릴 수 있어요. 이 중에 궁금한 게 있으신가요?

[예시 - 지원사업 안내]
사용자: 서울에서 카페 창업하려는데 지원금 있어?
너: (검색 도구 호출 후 결과 분석, 관련 있는 것만 골라서 한번에 안내)
검색해봤는데요, 카페 창업에 맞는 지원사업이 몇 가지 있어요.

"소상공인 정책자금 융자"는 최대 1억까지 저금리 대출이 가능하고, 소진공 홈페이지에서 신청하시면 돼요. 카페처럼 소규모 외식업 창업할 때 가장 많이 쓰는 제도예요.

"예비창업패키지"는 사업화 자금을 평균 5천만원 지원해주는 건데, 시제품 제작이나 마케팅 비용으로 쓸 수 있어요. 중소벤처기업부에서 운영하고 K-Startup 사이트에서 신청 가능합니다.

혹시 더 자세히 알고 싶은 사업이 있으면 말씀해주세요.

[지원사업 검색 규칙]
- 업종/지역 모르면 먼저 물어봐.
- 검색 결과에서 사용자 상황에 맞는 것만 골라서 안내해. 없으면 없다고 해. 지어내지 마.
- 관련 있는 사업이 여러 개면 한번에 자연스럽게 설명해. 하나씩 끊어서 물어보지 마.
- 각 사업마다 왜 이 사용자에게 맞는지, 얼마 지원되는지, 어디서 신청하는지를 포함해."""

# 범위 밖 키워드 감지용
OFF_TOPIC_RESPONSE = "저는 정부지원사업 검색과 영업신고서 작성만 도와드릴 수 있어요. 이 중에 궁금한 게 있으신가요?"

OFF_TOPIC_KEYWORDS = [
    "정치", "외교", "군사", "전쟁", "종교", "연예", "스포츠", "게임",
    "주식", "코인", "비트코인", "암호화폐", "투자종목",
    "날씨", "뉴스", "소설", "시 써줘", "노래", "가사",
    "코딩", "프로그래밍", "파이썬", "자바스크립트",
]

def is_off_topic(text: str) -> bool:
    """명백히 범위 밖인 질문 감지"""
    t = text.lower().strip()
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in t:
            return True
    return False


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory="."), name="files")

class ChatMessage(BaseModel):
    message: str

kernel = Kernel()
settings = None


def new_chat_history():
    ch = ChatHistory()
    ch.add_system_message(SYSTEM_PROMPT)
    return ch


chat_history = None


@app.on_event("startup")
async def startup_event():
    global settings, chat_history
    chat_service = AzureChatCompletion(
        deployment_name=AZURE_DEPLOYMENT_NAME,
        endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version="2024-12-01-preview"
    )
    kernel.add_service(chat_service)
    kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")
    kernel.add_plugin(GovSupportPlugin(), plugin_name="GovSupport")
    settings = chat_service.get_prompt_execution_settings_class()(service_id="default")
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
    chat_history = new_chat_history()
    print("backend ready")


@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


@app.post("/api/chat")
async def chat_endpoint(req: ChatMessage):
    user_text = req.message

    # 가드레일: 명백한 범위 밖 질문은 GPT 호출 없이 바로 차단
    if is_off_topic(user_text):
        chat_history.add_user_message(user_text)
        chat_history.add_assistant_message(OFF_TOPIC_RESPONSE)
        return {"reply": OFF_TOPIC_RESPONSE, "pdf_url": None}

    chat_history.add_user_message(user_text)

    result = await kernel.get_service("default").get_chat_message_content(
        chat_history=chat_history,
        settings=settings,
        kernel=kernel
    )
    bot_reply = result.content
    chat_history.add_message(result)

    pdf_url = None
    if ".pdf" in bot_reply:
        match = re.search(r"영업신고서_.*\.pdf", bot_reply)
        if match:
            pdf_url = f"/files/{match.group(0)}"

    return {
        "reply": bot_reply,
        "pdf_url": pdf_url
    }


@app.post("/api/reset")
async def reset_chat():
    global chat_history
    chat_history = new_chat_history()
    return {"status": "ok"}
