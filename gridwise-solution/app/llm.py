from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def get_llm_model() -> str:
    return os.getenv("MODEL_NAME", "gpt-4o-mini")


def call_llm(prompt: str, model: Optional[str] = None) -> str:
    """
    Placeholder LLM integration for Step 2.

    This function is intentionally lightweight and provider-agnostic.
    Replace this implementation with your preferred provider (OpenAI, Azure OpenAI, etc.)
    when integrating into production.
    """
    model_name = model or get_llm_model()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Set it in your .env file before using the LLM integration."
        )

    return (
        f"[LLM Stub] model={model_name}\n"
        f"Prompt received: {prompt[:500]}\n"
        "This function is a placeholder until the actual LLM client integration is configured."
    )
