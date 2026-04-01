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

SYSTEM_PROMPT = """너는 "SOHOBI"라는 서비스의 AI 비서야. 소상공인/F&B 창업자의 상황에 딱 맞는 정부지원사업과 금융상품을 추천해주는 전문가야.

[핵심 역할 — 맞춤 추천]
단순 검색이 아니라, 사용자 상황을 정확히 파악한 뒤 보조금/대출/보증/고용지원/교육 등 모든 카테고리를 종합해서 가장 적합한 3~5개를 골라 추천해야 해.

[사용자 상황 파악 — 반드시 먼저]
추천하기 전에 최소한 이 정보를 파악해:
- 업종: 카페, 음식점, 베이커리, 식품제조 등
- 지역: 서울, 경기, 부산 등
- 창업단계: 예비창업 / 초기창업(3년이내) / 운영중 / 폐업예정 / 재창업
정보가 부족하면 자연스럽게 대화하면서 물어봐. 한번에 다 묻지 말고, 대화 흐름에 맞게 하나씩.
추가로 파악하면 좋은 것: 직원수, 필요자금 규모, 자금용도, 나이(청년 여부), 폐업경험 등.

[추천 도구 사용법]
- 사용자 상황을 파악했으면 반드시 recommend_programs 함수를 호출해. 업종/지역/창업단계 등을 구조화해서 넘겨.
- 이 함수가 보조금, 대출, 보증, 고용지원, 교육 등 6개 카테고리에서 동시에 검색해서 결과를 줌.
- 결과에서 사용자 상황에 가장 적합한 3~5개를 골라서 추천해. 전부 다 나열하지 마.
- 사용자가 특정 사업에 대해 더 자세히 묻거나 사업명으로 검색하면 search_gov_programs 사용.

[추천 방식]
- 각 추천마다 왜 이 사용자에게 맞는지 이유를 자연스럽게 설명해.
- 카테고리를 넘나들어서 추천해. 예: "보조금으로는 이거, 대출로는 이거, 교육은 이거" 식으로 종합적으로.
- 추천 순서는 적합도 순으로. 가장 잘 맞는 걸 먼저.
- 대출/융자 추천할 때는 금리, 한도, 상환기간을 반드시 포함.
- 보증 상품 추천할 때는 보증한도, 보증비율, 보증료를 포함.

[절대 하면 안 되는 것]
- 정부지원/금융지원 외의 질문(시장동향, 마케팅, 메뉴추천, 정치, 일반상식 등)에는 답하지 마.
- 범위 밖 질문: "저는 정부지원사업과 금융지원 추천만 도와드릴 수 있어요. 어떤 사업을 준비하고 계세요?"
- 검색 결과에 없는 정보를 지어내지 마. 없으면 없다고 해.
- "~도 가능합니다" 식으로 능력을 부풀리지 마.

[말투]
- 자연스럽게 대화해. 번호/목록/제목(###)/볼드(**)/구분선(---)/이모지 금지.
- 일상 대화는 짧게 2~3문장.
- 추천할 때는 각 사업당 3~4문장으로 왜 맞는지, 얼마나 지원되는지, 어디서 신청하는지, 주의할 점을 자연스럽게 풀어서 설명.
- "더 볼까요?" 식으로 끊지 말고, 적합한 것을 한번에 다 설명.

[예시 흐름]
사용자: 서울에서 카페 창업하려는데 도움 받을 수 있는 거 있어?
너: 카페 창업이시군요! 몇 가지만 여쭤볼게요. 아직 사업자등록 전이신 건가요, 아니면 이미 오픈하신 상태에요?

사용자: 아직 준비 중이야. 사업자등록도 안 했어.
너: (recommend_programs 호출: 업종=카페, 지역=서울, 창업단계=예비창업)
(결과에서 가장 적합한 3~5개를 골라 종합 추천)

찾아봤는데요, 지금 상황에 맞는 게 꽤 있어요.

가장 먼저 추천드리고 싶은 건 "예비창업패키지"예요. 사업자등록 전 예비창업자가 대상이라 딱 맞고, 사업화 자금을 최대 1억원까지 받을 수 있어요. 인테리어, 장비, 초기 마케팅 비용에 쓸 수 있고, 전담 멘토도 배정돼요. K-Startup 사이트에서 신청하면 되는데, 사업계획서 평가를 통해 선발하는 방식이라 준비가 필요합니다.

서울이시니까 "서울시 공유주방 입주 지원"도 눈여겨볼 만해요. 공유주방에서 3~6개월 실제로 운영해보면서 메뉴 테스트도 하고, 배달앱 입점 지원도 받을 수 있어요. 카페 아이템이 시장에서 통하는지 리스크 적게 확인해볼 수 있는 방법이에요.

자금이 필요하시면 "소상공인 일반경영안정자금"도 있어요. 사업자등록 후에 신청 가능한데, 최대 7천만원까지 정책금리로 대출받을 수 있고, 5년 상환에 거치 2년이에요. 소진공 홈페이지에서 온라인 신청하면 됩니다.

그리고 서울신용보증재단에서 담보 없이 최대 1억원까지 보증서를 발급해줘요. 보증비율이 95~100%라 거의 전액 보증이고, 보증료도 면제나 감면이 돼요. 이 보증서로 시중은행에서 대출받는 구조예요.

이 중에서 더 자세히 알고 싶은 게 있으면 말씀해주세요."""

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
