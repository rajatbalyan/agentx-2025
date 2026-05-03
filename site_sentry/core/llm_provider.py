# site_sentry/core/llm_provider.py
"""
LLM provider factory for Site-Sentry.
Default: NVIDIA NIM (free tier) using OpenAI-compatible API.
Supports: nvidia_nim, google, groq, openai
"""
from __future__ import annotations
from typing import Literal
import structlog
from langchain_core.language_models import BaseChatModel

logger = structlog.get_logger()

LLMRole = Literal["manager", "agent"]


def get_llm(role: LLMRole, config) -> BaseChatModel:
    """
    Get the appropriate LLM for the given role.

    Args:
        role: "manager" (planning/orchestration) or "agent" (code edits/analysis)
        config: SentryConfig instance

    Returns:
        A LangChain-compatible chat model
    """
    provider = config.llm.provider
    api_key = config.api_key

    if not api_key:
        raise ValueError(
            f"No API key found. Set NVIDIA_API_KEY in your .env file.\n"
            f"Get a free key at: https://build.nvidia.com"
        )

    model_name = (
        config.llm.manager_model if role == "manager" else config.llm.agent_model
    )

    logger.info("Initializing LLM", provider=provider, model=model_name, role=role)

    if provider == "nvidia_nim":
        return _get_nvidia_nim(model_name, config, api_key)
    elif provider == "google":
        return _get_google(model_name, config, api_key)
    elif provider == "groq":
        return _get_groq(model_name, config, api_key)
    elif provider == "openai":
        return _get_openai(model_name, config, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose: nvidia_nim, google, groq, openai")


def _get_nvidia_nim(model_name: str, config, api_key: str) -> BaseChatModel:
    """NVIDIA NIM — OpenAI-compatible, free tier, 40 RPM."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("Run: pip install langchain-openai")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=config.llm.base_url,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        # NIM-specific: respect rate limits with retries
        max_retries=3,
    )


def _get_google(model_name: str, config, api_key: str) -> BaseChatModel:
    """Google Gemini — free tier, 15 RPM, 1500 req/day."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError("Run: pip install langchain-google-genai")

    return ChatGoogleGenerativeAI(
        model=model_name or "gemini-2.0-flash",
        google_api_key=api_key,
        temperature=config.llm.temperature,
        max_output_tokens=config.llm.max_tokens,
        convert_system_message_to_human=True,
    )


def _get_groq(model_name: str, config, api_key: str) -> BaseChatModel:
    """Groq — ultra-fast inference, free tier, 14400 req/day."""
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError("Run: pip install langchain-groq")

    return ChatGroq(
        model=model_name or "llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )


def _get_openai(model_name: str, config, api_key: str) -> BaseChatModel:
    """Standard OpenAI."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("Run: pip install langchain-openai")

    return ChatOpenAI(
        model=model_name or "gpt-4o-mini",
        api_key=api_key,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )
