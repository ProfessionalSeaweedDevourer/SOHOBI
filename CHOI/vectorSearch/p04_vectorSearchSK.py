import asyncio
from typing import Annotated
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from p03_vectorSearch import perform_vector_search # 직접 만드신 p03_vectorSearch.py에서 가져오기

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
    # 2. 커널 초기화
    kernel = Kernel()

    # 3. 채팅 서비스 추가
    # 사용자가 제공한 전체 URL: https://student02-11-1604-resource.cognitiveservices.azure.com/openai/deployments/gpt-4o-mini-2024-07-18.ft-d02f43fca9714ccca92d48d218362181/chat/completions?api-version=2024-05-01-preview
    
    # 1) Endpoint: 리소스 주소까지만 입력
    ENDPOINT = "https://student02-11-1604-resource.cognitiveservices.azure.com/"
    
    # 2) Deployment Name: URL 중간의 deployments/ 뒤에 있는 문자열
    DEPLOYMENT_NAME = "gpt-4o-mini-2024-07-18.ft-d02f43fca9714ccca92d48d218362181"
    
    # 3) API Key
    API_KEY = "BQrdUVZyMVUpWd6Xtyvb7BAixaLikbxZlCzF5Zoj98f2pWYR6tJfJQQJ99CBACHYHv6XJ3w3AAAAACOGSqpw"

    chat_service = AzureChatCompletion(
        deployment_name=DEPLOYMENT_NAME,
        endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version="2024-05-01-preview" # 제공해주신 URL의 쿼리 스트링 값과 일치시킴
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

        print("\n[에이전트의 최종 답변]")
        print(result.content)
    except Exception as e:
        import traceback
        print("\n[서비스 호출 오류 상세]")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        # 오류가 지속될 경우 아래 주석을 해제하여 상세 로그를 확인하세요.
        # traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())