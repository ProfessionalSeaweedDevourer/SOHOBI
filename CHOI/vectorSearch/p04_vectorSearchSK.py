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
        description=(
            "창업 관련 법령을 벡터 검색합니다. "
            "식품위생법, 소방시설법, 건축법, 근로기준법, 부가가치세법, 소득세법, "
            "상가건물 임대차보호법, 중소기업창업 지원법, 공중위생관리법, 최저임금법, "
            "소상공인 보호법, 국민건강증진법, 주세법, 폐기물관리법 및 각 시행령·시행규칙을 포함합니다. "
            "결과가 없으면 추가 검색하지 마세요."
        )
    )
    def search_legal_docs(
        self,
        query: Annotated[str, "검색할 구체적인 질문 키워드"]
    ) -> str:
        # 검색 수행 (top_k를 적절히 조절)
        results = perform_vector_search(query, top_k=5)
        
        if not results:
            return "검색 결과가 없습니다. 사용자에게 정보를 찾을 수 없다고 안내하세요."
        
        # 모델이 읽기 좋게 컨텍스트 구성 (장/절 계층 정보 포함)
        context = []
        for doc in results:
            hierarchy = ""
            if doc.get('chapterTitle'):
                hierarchy += doc['chapterTitle'] + " > "
            if doc.get('sectionTitle'):
                hierarchy += doc['sectionTitle'] + " > "

            law_info = "[%s 제%s조(%s)] %s\n%s" % (
                doc.get('lawName', '법령미상'),
                doc.get('articleNo', ''),
                doc.get('articleTitle', ''),
                hierarchy,
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
        "당신은 소상공인 창업 법령 전문 안내 도우미입니다.\n"
        "검색 도구(search_legal_docs)로 법령을 검색하여 답변하세요.\n\n"
        "답변 규칙:\n"
        "1. 반드시 [법령명 제N조(조문제목)] 형식으로 근거 조항을 명시하세요.\n"
        "2. 검색 결과에 없는 내용은 추측하지 마세요.\n"
        "3. 여러 법령이 관련되면 법령별로 구분하여 안내하세요.\n"
        "4. 시행령/시행규칙의 세부 기준이 있으면 함께 언급하세요.\n"
        "5. 검색 결과가 불충분하면 '해당 정보를 찾을 수 없습니다'라고 답하세요.\n"
        "6. 한 번의 검색으로 충분하지 않으면, 키워드를 바꿔 최대 1회 추가 검색할 수 있습니다.\n\n"
        "답변 말미 필수 요소 (반드시 포함):\n"
        "- 면책 조항: '본 답변은 법적 효력을 갖는 조언이 아니며, 일반적인 법령 정보 안내입니다.'\n"
        "- 개정 가능성: '인용된 법령은 개정될 수 있으므로 최신 법령을 확인하시기 바랍니다.'\n"
        "- 전문가 상담 권고: '정확한 적용을 위해 관련 전문가(변호사, 행정사 등)와 상담하시기를 권장합니다.'\n"
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