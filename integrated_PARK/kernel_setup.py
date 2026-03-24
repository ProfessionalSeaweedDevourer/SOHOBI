import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import openai
from dotenv import load_dotenv

load_dotenv()

_TOKEN_PROVIDER = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)


def get_kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    kernel.add_service(
        AzureChatCompletion(
            service_id="sign_off",
            deployment_name=os.getenv("AZURE_DEPLOYMENT_NAME"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=api_key if api_key else None,
            ad_token_provider=None if api_key else _TOKEN_PROVIDER,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
        )
    )
    return kernel


def get_signoff_client() -> openai.AsyncAzureOpenAI:
    return openai.AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_SIGNOFF_ENDPOINT"),
        azure_ad_token_provider=_TOKEN_PROVIDER,
        api_version="2025-04-01-preview",
        timeout=220.0,  # Container Apps 240초 timeout 이내에 Python이 먼저 에러 이벤트 전송하도록 상향
    )
