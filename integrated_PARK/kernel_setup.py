import os
import threading
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

_kernel: sk.Kernel | None = None
_kernel_lock = threading.Lock()


def _deployment(specific_var: str) -> str:
    """에이전트별 env var → 없으면 공통 AZURE_DEPLOYMENT_NAME으로 fallback"""
    return os.getenv(specific_var) or os.getenv("AZURE_DEPLOYMENT_NAME") or ""


def _build_kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    # Azure AI Foundry 프로젝트 엔드포인트는 base_url 형식 사용
    # 예: https://<resource>.services.ai.azure.com/api/projects/<project>/openai/v1
    base_url = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    agent_services = [
        ("admin",    "AZURE_ADMIN_DEPLOYMENT"),
        ("finance",  "AZURE_FINANCE_DEPLOYMENT"),
        ("legal",    "AZURE_LEGAL_DEPLOYMENT"),
        ("location", "AZURE_LOCATION_DEPLOYMENT"),
        ("chat",     "AZURE_CHAT_DEPLOYMENT"),
        ("router",   "AZURE_ROUTER_DEPLOYMENT"),
    ]
    for service_id, env_var in agent_services:
        kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=_deployment(env_var),
                base_url=base_url,
                api_key=api_key if api_key else None,
                ad_token_provider=None if api_key else _TOKEN_PROVIDER,
                api_version=api_version,
            )
        )
    return kernel


def get_kernel() -> sk.Kernel:
    global _kernel
    if _kernel is None:
        with _kernel_lock:
            if _kernel is None:
                _kernel = _build_kernel()
    return _kernel


def get_signoff_client() -> openai.AsyncAzureOpenAI:
    signoff_base_url = (
        os.getenv("AZURE_SIGNOFF_ENDPOINT")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
        or ""
    )
    return openai.AsyncAzureOpenAI(
        azure_endpoint=signoff_base_url,
        azure_ad_token_provider=_TOKEN_PROVIDER,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        timeout=220.0,
    )