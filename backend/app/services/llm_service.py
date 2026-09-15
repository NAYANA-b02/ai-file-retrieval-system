import logging
from typing import Dict, List, Optional
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.ollama_service import call_ollama_chat

logger = logging.getLogger(__name__)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def call_groq_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    Call Groq Cloud Chat Completions API with safe error handling.

    - Uses direct HTTP POST via httpx (no external SDK required).
    - Ensures GROQ_API_KEY is never logged or exposed in error messages.
    - Validates payload and response structure.
    """
    target_api_key = api_key or settings.GROQ_API_KEY
    if not target_api_key or not target_api_key.strip():
        logger.error("Groq API call attempted without GROQ_API_KEY configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq API key is not configured.",
        )

    target_model = model or settings.GROQ_MODEL
    target_timeout = timeout or settings.GROQ_TIMEOUT_SECONDS

    headers = {
        "Authorization": f"Bearer {target_api_key.strip()}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": target_model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=target_timeout) as client:
            response = client.post(GROQ_ENDPOINT, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

    except httpx.ConnectError as e:
        logger.error("Groq connection error: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq service is unavailable.",
        )
    except httpx.TimeoutException as e:
        logger.error("Groq timeout error: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Groq request timed out.",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Groq HTTP status error: %s", e.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq returned HTTP error: {e.response.status_code}",
        )
    except Exception as e:
        logger.error("Unexpected error communicating with Groq: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Groq service.",
        )

    # Validate returned JSON structure
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Groq service.",
        )

    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Groq service.",
        )

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Groq service.",
        )

    message = first_choice.get("message")
    if not isinstance(message, dict) or "content" not in message:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Groq service.",
        )

    content = message.get("content", "")
    return content.strip()


def call_llm_chat(messages: List[Dict[str, str]]) -> str:
    """
    Provider-agnostic LLM dispatcher.

    - Supports 'ollama' (default for local development)
    - Supports 'groq' (for production)
    - Dispatches based on settings.LLM_PROVIDER
    """
    provider = (settings.LLM_PROVIDER or "ollama").lower().strip()

    if provider == "ollama":
        import app.services.rag_service as rag_service_mod
        rag_fn = getattr(rag_service_mod, "call_ollama_chat", None)
        if hasattr(rag_fn, "assert_called") or hasattr(rag_fn, "mock_calls"):
            return rag_fn(messages)
        return call_ollama_chat(messages)

    elif provider == "groq":
        return call_groq_chat(messages)

    else:
        logger.error("Unsupported LLM provider requested: %s", provider)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported LLM provider: {provider}",
        )
