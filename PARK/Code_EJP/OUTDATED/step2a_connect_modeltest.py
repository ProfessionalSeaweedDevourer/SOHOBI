import os
import asyncio
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory
from dotenv import load_dotenv

load_dotenv()

kernel = sk.Kernel()
kernel.add_service(
    AzureChatCompletion(
        service_id="sign_off",
        deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-12-01-preview",
    )
)

async def test_basic():
    chat_service = kernel.get_service("sign_off")
    history = ChatHistory()
    history.add_user_message("안녕하세요. 테스트입니다. 한 문장으로 응답하세요.")
    
    result = await chat_service.get_chat_message_content(
        chat_history=history,
        settings=AzureChatPromptExecutionSettings(),
    )
    print(result)

asyncio.run(test_basic())