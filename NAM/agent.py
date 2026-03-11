import asyncio
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory

# 어제 만들어둔 플러그인 가져오기 (동일한 폴더에 BusinessPlugin.py 가 있어야 함)
from BusinessPlugin import FoodBusinessPlugin 

async def main():
    kernel = Kernel()

    # 💡 [여기 수정!] 방금 파운드리에서 복사한 값들을 따옴표 안에 넣으세요.
    chat_service = AzureChatCompletion(
        deployment_name="gpt-4o", # 아까 모델 배포할 때 쓴 이름
        endpoint="https://agentpdf.cognitiveservices.azure.com/", 
        api_key="여기에_키_값을_넣어주세요",
        api_version="2024-12-01-preview"
    )
    kernel.add_service(chat_service)

    # 에이전트에게 플러그인(도구) 장착 및 자동 사용 허락
    kernel.add_plugin(FoodBusinessPlugin(), plugin_name="BusinessDoc")
    settings = chat_service.get_prompt_execution_settings_class()(service_id="default")
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # 에이전트 시스템 프롬프트
    history = ChatHistory()
    system_prompt = """
    당신은 1인 창업가를 돕는 친절하고 전문적인 AI 행정 비서입니다. 
    사용자가 '식품 영업 신고서'를 만들고 싶어 하면, 아래의 정보를 대화를 통해 수집하세요.

    [필수 정보]
    1. 대표자 정보: 이름, 주민등록번호, 집 주소, 휴대전화 번호
    2. 영업소 정보: 상호명, 매장 전화번호, 매장 주소, 영업의 종류, 매장 면적

    - 취조하듯 묻지 말고, 1~2개씩 대화하듯 자연스럽게 질문하세요.
    - 모든 정보가 수집되면 반드시 `BusinessDoc-create_food_report` 도구를 호출하세요.
    """
    history.add_system_message(system_prompt)

    print("="*60)
    print("🤖 Azure 기반 에이전트 가동 준비 완료! (종료: exit)")
    print("="*60)
    print("에이전트: 안녕하세요 사장님! 어떤 창업 서류 준비를 도와드릴까요?")
    
    # 채팅 루프
    while True:
        user_input = input("\n사장님: ")
        if user_input.strip().lower() in ['exit', 'quit', '종료']:
            print("대화를 종료합니다.")
            break

        history.add_user_message(user_input)

        try:
            result = await chat_service.get_chat_message_content(
                chat_history=history,
                settings=settings,
                kernel=kernel
            )
            print(f"\n에이전트: {result.content}")
            history.add_message(result)
            
        except Exception as e:
            print(f"\n[오류 발생]: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())