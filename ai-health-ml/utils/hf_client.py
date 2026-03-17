from __future__ import annotations

from typing import Any

import httpx

from utils.config import get_env


_LAST_HF_ERROR: str = ""


def get_last_hf_error() -> str:
    """
    Returns the last Hugging Face error observed by this process (for debugging).
    Never includes the API key.
    """
    return _LAST_HF_ERROR


def call_huggingface_api(
    prompt: str,
    *,
    model_env: str = "HF_DISEASE_MODEL",
    default_model: str = "HuggingFaceH4/zephyr-7b-beta:fastest",
) -> str:
    """
    Safe Hugging Face Inference API (READ-ONLY) wrapper.

    - Uses HF_API_KEY (read-only token) from .env/environment.
    - Uses Hugging Face Router (OpenAI-compatible) for inference:
      POST https://router.huggingface.co/v1/chat/completions
    - Never raises; returns "" on any error/misconfiguration.
    """
    global _LAST_HF_ERROR

    api_key = get_env("HF_API_KEY")
    if not api_key:
        _LAST_HF_ERROR = "HF_API_KEY missing"
        print("No API key, skipping online search")
        return ""

    # Use HF Router "Responses API" (OpenAI-compatible, non-chat),
    # which works better for instruction-following text->text models.
    model = get_env(model_env, default_model) or default_model
    url = "https://router.huggingface.co/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "temperature": 0.2,
        "max_output_tokens": 256,
    }

    try:
        print("Calling Hugging Face API...")
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                try:
                    err = resp.json()
                except Exception:
                    err = resp.text
                _LAST_HF_ERROR = f"HF {resp.status_code}: {str(err)[:300]}"
                print("API failed:", _LAST_HF_ERROR)
                return ""
            data = resp.json()
            print("API response received")

        # Responses API:
        # Prefer "output_text" when present; else parse output blocks.
        _LAST_HF_ERROR = ""

        if isinstance(data, dict):
            if "output_text" in data:
                return str(data.get("output_text") or "").strip()
            out = data.get("output", [])
            if isinstance(out, list):
                texts: list[str] = []
                for block in out:
                    if not isinstance(block, dict):
                        continue
                    content = block.get("content")
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                t = str(c.get("text") or "").strip()
                                if t:
                                    texts.append(t)
                if texts:
                    return "\n".join(texts).strip()
        return ""
    except Exception:
        _LAST_HF_ERROR = "HF call failed (exception)"
        print("API failed:", _LAST_HF_ERROR)
        return ""

