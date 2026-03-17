import asyncio
import os
from typing import Annotated
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from p03_vectorSearch import perform_vector_search # 직접 만드신 p03_vectorSearch.py에서 가져오기

# .env 로드
load_dotenv()

# 1. 법률/세무 지식 검색용 커스텀 플러그인 정의
class LegalKnowledgePlugin:
    @kernel_function(
        name="search_legal_docs",
        description="F&B 창업 관련 법률, 위생, 세무 정보를 벡터 DB에서 검색합니다."
    )
    def search_legal_docs(
        self, 
        query: Annotated[str, "검색할 질문 내용"]
    ) -> str:
        # p03_vectorSearch.py에 정의된 함수 호출
        results = perform_vector_search(query, top_k=2)
        
        if not results:
            return "관련된 법령 정보를 찾을 수 없습니다."
        
        # 에이전트가 읽기 좋게 텍스트로 합치기
        context = []
        for doc in results:
            context.append("[%s] %s" % (doc.get('title', '제목 없음'), doc.get('content', '내용 없음')))
        
        return "\n\n".join(context)

async def main():
    kernel = Kernel()

    # --- 환경 변수에서 설정 정보 로드 ---
    ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    # API 버전을 명시적으로 .env에서 가져오되 없으면 기본값 사용
    API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

    chat_service = AzureChatCompletion(
        deployment_name=DEPLOYMENT_NAME,
        endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VERSION
    )
    kernel.add_service(chat_service)

    # 4. 우리가 만든 플러그인 등록
    kernel.add_plugin(LegalKnowledgePlugin(), plugin_name="LegalSearch")

    # 5. 실행 테스트 (Function Calling 설정)
    from semantic_kernel.contents import ChatHistory

    # Pydantic ValidationError를 방지하기 위해 생성자에서 behavior를 정의
    settings = AzureChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto()
    )

    history = ChatHistory()
    history.add_user_message("카페 창업할 때 보건증 검사 항목이 뭐야?")

    try:
        # 에이전트가 질문을 보고 'LegalSearch' 플러그인이 필요함을 스스로 판단하여 호출합니다.
        result = await chat_service.get_chat_message_content(
            chat_history=history,
            kernel=kernel,
            settings=settings
        )

        print("\n[에이전트 답변]:")
        print(result.content)

    except Exception as e:
        print("\n[오류 발생]: %s" % e)

if __name__ == "__main__":
    asyncio.run(main())