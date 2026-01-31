"""Small wrapper for OpenAI Chat API to support multiple system prompts and structured extraction.

This module centralizes calls to OpenAI and provides a helper to ask for JSON-structured
contract extraction results.
"""
import os
from typing import List, Dict, Any

_OPENAI_AVAILABLE = True
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
    _OPENAI_AVAILABLE = False


def _get_client():
    """Lazily construct and return an OpenAI client.

    Raises a RuntimeError with actionable guidance if the package or API key is missing.
    """
    if not _OPENAI_AVAILABLE or OpenAI is None:
        raise RuntimeError(
            "The 'openai' Python package (v1+) is required but not available. "
            "Install with: pip install openai"
        )
    key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_key")
    if not key:
        raise RuntimeError(
            "OpenAI API key not found. Set the environment variable OPENAI_API_KEY or openai_key before running."
        )
    try:
        client = OpenAI(api_key=key)
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to construct OpenAI client: {e}")


def call_openai_chat(messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Call the OpenAI chat completions endpoint and return the raw response.

    This wrapper does not pass temperature — callers choose models that provide
    the desired deterministic behavior by default.
    """
    import time
    import logging

    logger = logging.getLogger(__name__)
    logger.info("OpenAI call start: model=%s messages=%d", model, len(messages))
    client = _get_client()
    start = time.time()
    try:
        resp = client.chat.completions.create(model=model, messages=messages)
        duration = time.time() - start
        logger.info("OpenAI call finished in %.2fs", duration)
        return resp
    except Exception as e:
        duration = time.time() - start
        logger.error("OpenAI call failed in %.2fs: %s", duration, e)
        # surface the underlying API error with context
        raise RuntimeError(f"OpenAI API call failed: {e}")


def extract_contract_fields(text: str, system_prompts: List[str] = None, model: str = "gpt-4o-mini") -> str:
    """Ask the LLM to extract contract fields and return the assistant content (expected JSON string).

    system_prompts: list of system-level prompts to prepend. The user content asks for structured JSON.
    """
    # allow callers to pass focused system prompts; otherwise load defaults
    if system_prompts is None:
        try:
            from . import prompts as _prompts
            system_prompts = _prompts.get_default_system_prompts()
        except Exception:
            system_prompts = []

    messages = []
    for sp in system_prompts:
        messages.append({"role": "system", "content": sp})

    user_prompt = (
        "You are a legal contracts analysis assistant.\n"
        "Extract the following fields from the provided contract text and return a single JSON object. "
        "Fields: contract_type, parties (list), effective_date, termination_clause (text), governing_law, "
        "amounts (list), obligations (list), liabilities (list), confidentiality (boolean + summary), "
        "clauses (list of {title, text}), risk_indicators (list), overall_risk (Low/Medium/High).\n"
        "Return strictly valid JSON. If you can't find a field, use null or an empty list as appropriate.\n\n"
        "CONTRACT TEXT:\n" + text
    )

    messages.append({"role": "user", "content": user_prompt})

    resp = call_openai_chat(messages=messages, model=model)
    # return assistant message (handle typed and dict-like responses)
    try:
        assistant = resp.choices[0].message.content
    except Exception:
        assistant = resp["choices"][0]["message"]["content"]
    return assistant


__all__ = ["call_openai_chat", "extract_contract_fields"]
