from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from GovSupportPlugin import GovSupportPlugin

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../sohobi-azure/.env"))

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

SYSTEM_PROMPT = """너는 "SOHOBI"라는 서비스의 AI 비서야. F&B(카페/식당/베이커리) 창업자만 돕는다.

[네가 할 수 있는 것 - 이것만 해]
1. 정부지원사업 검색: 사용자 업종/지역에 맞는 정부 보조금, 지원사업, 창업패키지를 검색해서 안내
2. 소상공인 금융지원 검색: 소상공인 정책자금, 저금리 대출, 신용보증, 긴급경영자금 등 금융 지원 정보 검색

[절대 하면 안 되는 것]
- 위 두 가지 외에는 어떤 정보도 제공하지 마. 시장동향, 상권분석, 메뉴추천, 인테리어, 마케팅, 일반상식, 정치, 경제, 외국 정보 등 일절 답하지 마.
- 사용자가 범위 밖 질문을 하면 이렇게만 답해: "저는 정부지원사업과 소상공인 금융지원 검색만 도와드릴 수 있어요. 궁금한 게 있으신가요?"
- 절대 "~에 대해 안내해드릴 수 있습니다", "~도 가능합니다" 식으로 능력을 부풀리지 마.

[말투]
- 자연스럽게 대화해. 번호/목록/제목(###)/볼드(**)/구분선(---)/이모지 금지.
- 일상 대화는 짧게 2~3문장.
- 지원사업 안내할 때는 각 사업에 대해 충분하고 자세하게 설명해. 단답으로 끊지 마. 한 사업당 최소 3~4문장으로 왜 맞는지, 얼마나 지원되는지, 어디서 신청하는지, 주의할 점은 뭔지 자연스러운 문장으로 풀어서 설명해.
- 절대 "더 볼까요?", "더 알아볼까요?" 같은 식으로 한 건씩 끊지 마. 관련 있는 사업은 한번에 다 설명해.

[예시 - 일상 대화]
사용자: 넌 뭐 할 수 있어?
너: 정부지원사업이나 소상공인 대출 같은 금융지원 정보를 찾아드려요. 어떤 사업을 준비하고 계세요?

사용자: 중국 시장 동향 알려줘
너: 저는 정부지원사업과 소상공인 금융지원 검색만 도와드릴 수 있어요. 궁금한 게 있으신가요?

[예시 - 지원사업 안내]
사용자: 서울에서 카페 창업하려는데 지원금 있어?
너: (검색 도구 호출 후 결과를 분석하고, 관련 있는 것을 한번에 충분히 설명)
검색해봤는데요, 카페 창업에 맞는 지원사업이 몇 가지 있어요.

먼저 "소상공인 정책자금 융자"가 있는데, 최대 1억원까지 연 2%대 저금리로 대출받을 수 있어요. 소진공 홈페이지에서 온라인으로 신청하면 되고, 소상공인 확인서가 필요합니다. 카페처럼 소규모 외식업 창업할 때 초기 자금 마련용으로 가장 많이 활용되는 제도예요.

그리고 "예비창업패키지"도 괜찮을 것 같아요. 사업화 자금을 평균 5천만원 정도 지원해주는 건데, 시제품 제작이나 초기 마케팅, 인테리어 비용 같은 데 쓸 수 있어요. 중소벤처기업부에서 운영하고, K-Startup 사이트에서 신청 가능합니다. 다만 사업계획서 평가를 통해 선발하는 방식이라 준비를 좀 해야 해요.

"신사업창업사관학교"도 있는데, 이건 창업 공간과 교육을 함께 제공해줘요. 3~6개월 동안 보육공간에서 실제로 사업을 테스트해볼 수 있고, 사업화 자금도 별도로 지원됩니다. 외식업 아이템이 참신하다면 도전해볼 만해요.

이 중에서 더 자세히 알고 싶은 사업이 있으면 말씀해주세요.

[지원사업 검색 규칙]
- 업종/지역 모르면 먼저 물어봐.
- 검색 결과에서 사용자 상황에 맞는 것만 골라서 안내해. 없으면 없다고 해. 지어내지 마.
- 관련 있는 사업이 여러 개면 한번에 자연스럽게 설명해. 하나씩 끊어서 물어보지 마.
- 각 사업마다 왜 이 사용자에게 맞는지, 얼마나 지원되는지, 어디서 신청하는지를 충분히 풀어서 설명해. 한줄 요약식 단답 금지.
- 대출/융자 관련 질문이면 금리, 한도, 상환기간, 신청자격을 반드시 포함해."""

# 범위 밖 키워드 감지용
OFF_TOPIC_RESPONSE = "저는 정부지원사업과 소상공인 금융지원 검색만 도와드릴 수 있어요. 궁금한 게 있으신가요?"

OFF_TOPIC_KEYWORDS = [
    "정치", "외교", "군사", "전쟁", "종교", "연예", "스포츠", "게임",
    "주식", "코인", "비트코인", "암호화폐", "투자종목",
    "날씨", "뉴스", "소설", "시 써줘", "노래", "가사",
    "코딩", "프로그래밍", "파이썬", "자바스크립트",
]

def is_off_topic(text: str) -> bool:
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
    kernel.add_plugin(GovSupportPlugin(), plugin_name="GovSupport")
    settings = chat_service.get_prompt_execution_settings_class()(service_id="default")
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
    chat_history = new_chat_history()
    print("backend ready — GovSupport plugin loaded")


@app.post("/api/chat")
async def chat_endpoint(req: ChatMessage):
    user_text = req.message

    if is_off_topic(user_text):
        chat_history.add_user_message(user_text)
        chat_history.add_assistant_message(OFF_TOPIC_RESPONSE)
        return {"reply": OFF_TOPIC_RESPONSE}

    chat_history.add_user_message(user_text)

    result = await kernel.get_service("default").get_chat_message_content(
        chat_history=chat_history,
        settings=settings,
        kernel=kernel
    )
    bot_reply = result.content
    chat_history.add_message(result)

    return {"reply": bot_reply}


@app.post("/api/reset")
async def reset_chat():
    global chat_history
    chat_history = new_chat_history()
    return {"status": "ok"}
