import asyncio
import os
from typing import Annotated
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents import ChatHistory
from p03_vectorSearch import perform_vector_search

# .env 로드
load_dotenv()

# 1. 커스텀 플러그인 (p03_vectorSearch 연동)
class LegalKnowledgePlugin:
    @kernel_function(
        name="search_legal_docs",
        description="식품위생법, 보건증, 창업 위생 관련 법령 정보를 검색합니다. 결과가 없으면 추가 검색하지 마세요."
    )
    def search_legal_docs(
        self, 
        query: Annotated[str, "검색할 구체적인 질문 키워드"]
    ) -> str:
        # 검색 수행 (top_k를 적절히 조절)
        results = perform_vector_search(query, top_k=3)
        
        if not results:
            return "검색 결과가 없습니다. 사용자에게 정보를 찾을 수 없다고 안내하세요."
        
        # 모델이 읽기 좋게 컨텍스트 구성
        context = []
        for doc in results:
            # 실제 인덱스 필드명에 맞춰 수정 (lawName, content, articleNo 등)
            law_info = "[%s 제%s조] %s" % (
                doc.get('lawName', '법령미상'), 
                doc.get('articleNo', ''), 
                doc.get('content', doc.get('fullText', '내용 없음'))
            )
            context.append(law_info)
            
        return "\n\n".join(context)

async def main():
    kernel = Kernel()

    # --- 환경 설정 ---
    ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

    chat_service = AzureChatCompletion(
        deployment_name=DEPLOYMENT_NAME,
        endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VERSION
    )
    kernel.add_service(chat_service)
    kernel.add_plugin(LegalKnowledgePlugin(), plugin_name="LegalSearch")

    # 2. 실행 설정 (무한 반복 방지 핵심)
    # auto_invoke_counting_limit: 함수 호출 최대 횟수를 제한 (기본값은 보통 5회 이상임)
    settings = AzureChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke_counting_limit=2)
    )

    # 3. 시스템 프롬프트 추가 (가이드라인 제시)
    history = ChatHistory()
    history.add_system_message(
        "당신은 법령 전문 안내 도우미입니다. "
        "제공된 검색 도구(search_legal_docs)를 사용하여 답변하세요. "
        "만약 검색 결과에 답이 없다면, 억지로 계속 검색하지 말고 아는 범위까지만 답하거나 정보를 찾을 수 없다고 하세요. "
        "법령명과 조항 번호를 반드시 언급하며 답변하세요."
    )
    
    user_input = input("질문 : ")  #"카페 창업 시 보건증 검사 항목과 관련 법령을 알려줘."
    history.add_user_message(user_input)

    print("에이전트가 법령을 검색 중입니다...")

    try:
        # 에이전트 호출
        result = await chat_service.get_chat_message_contents(
            chat_history=history,
            settings=settings,
            kernel=kernel
        )
        
        if result:
            print("\n[최종 답변]:")
            print(result[0].content)
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())