"""客户端工具函数

提供用于创建各种LLM客户端的辅助函数，支持多种模型提供商。
"""

import logging
import os

import openai

logger = logging.getLogger(__name__)


def create_openai_client_for_model(model_name: str) -> openai.OpenAI:
    """根据模型名称创建正确的OpenAI客户端

    这个函数会根据模型名称自动选择正确的API配置：
    - GEMINI模型：使用GOOGLE_API_KEY和GOOGLE_BASE_URL
    - OpenAI/Qwen等模型：使用OPENAI_API_KEY和OPENAI_BASE_URL

    Args:
        model_name: 模型名称（如 "gpt-4o", "gemini-2.5-pro-preview-05-06", "qwen3-max"）

    Returns:
        配置好的OpenAI客户端

    Examples:
        >>> client = create_openai_client_for_model("gemini-2.5-pro-preview-05-06")
        >>> # 将使用GOOGLE_API_KEY和GOOGLE_BASE_URL

        >>> client = create_openai_client_for_model("gpt-4o")
        >>> # 将使用OPENAI_API_KEY和OPENAI_BASE_URL

        >>> client = create_openai_client_for_model("qwen3-max")
        >>> # 将使用OPENAI_API_KEY和OPENAI_BASE_URL (阿里云兼容OpenAI接口)
    """
    # 检查是否是GEMINI模型
    if model_name.lower().startswith("gemini-") or model_name.upper().startswith("GEMINI_"):
        # 使用GOOGLE API配置
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_base_url = os.getenv("GOOGLE_BASE_URL")

        if not google_api_key:
            logger.warning(
                f"[VIGIL] GOOGLE_API_KEY not set for GEMINI model {model_name}, "
                f"falling back to default OpenAI client"
            )
            return openai.OpenAI()

        if google_base_url:
            logger.info(f"[VIGIL] Using GEMINI model via OpenAI-compatible interface at {google_base_url}")
            return openai.OpenAI(
                api_key=google_api_key,
                base_url=google_base_url,
            )
        else:
            logger.warning(
                f"[VIGIL] GOOGLE_BASE_URL not set for GEMINI model {model_name}, "
                f"using default base_url"
            )
            return openai.OpenAI(api_key=google_api_key)
    else:
        # 使用OpenAI API配置（包括Qwen等OpenAI兼容模型）
        # openai.OpenAI() 会自动读取 OPENAI_API_KEY 和 OPENAI_BASE_URL 环境变量
        return openai.OpenAI()
