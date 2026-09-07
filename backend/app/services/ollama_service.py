import logging
from typing import Dict, List, Optional
import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def call_ollama_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    Call the local Ollama chat API (/api/chat) with strict error handling.

    - Exclusively local; no external cloud calls.
    - Maps connection failure to 503 Service Unavailable.
    - Maps request timeout to 504 Gateway Timeout.
    - Maps HTTP or JSON parse errors to 502 Bad Gateway.
    - Returns the generated assistant message content.
    """
    target_model = model or settings.OLLAMA_MODEL
    target_base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
    target_timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS
    endpoint = f"{target_base_url}/api/chat"

    payload = {
        "model": target_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
        },
    }

    try:
        with httpx.Client(timeout=target_timeout) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

    except httpx.ConnectError as e:
        logger.error("Ollama connection error at %s: %s", endpoint, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is unavailable. Please ensure local Ollama is running.",
        )
    except httpx.TimeoutException as e:
        logger.error("Ollama timeout at %s: %s", endpoint, e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Ollama request timed out.",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Ollama HTTP status error %s: %s", e.response.status_code, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama returned HTTP error: {e.response.status_code}",
        )
    except Exception as e:
        logger.error("Unexpected error communicating with Ollama: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Ollama service.",
        )

    # Validate returned JSON structure
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Ollama service.",
        )

    message = data.get("message")
    if not isinstance(message, dict) or "content" not in message:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Ollama service.",
        )

    content = message.get("content", "")
    return content.strip()
