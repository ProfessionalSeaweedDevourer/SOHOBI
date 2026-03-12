import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from dotenv import load_dotenv

load_dotenv()


def get_kernel() -> sk.Kernel:
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
    return kernel
