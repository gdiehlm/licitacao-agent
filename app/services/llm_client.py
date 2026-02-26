import json
import os
from typing import Any, Dict, List

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "120"))


class LLMError(RuntimeError):
    pass


def _build_model(enable_google_grounding: bool = False) -> genai.GenerativeModel:
    if not GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY não configurada.")

    genai.configure(api_key=GEMINI_API_KEY)

    tools = None
    if enable_google_grounding:
        tools = [{"google_search_retrieval": {}}]

    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        tools=tools,
        generation_config={"temperature": 0.2},
    )


def gemini_chat(messages: List[Dict[str, str]], enable_google_grounding: bool = False) -> Dict[str, Any]:
    """Executa chat no Gemini e retorna texto + fontes de grounding quando disponíveis."""
    model = _build_model(enable_google_grounding=enable_google_grounding)

    chat_history = []
    if len(messages) > 1:
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(
            messages[-1]["content"],
            request_options={"timeout": GEMINI_TIMEOUT},
        )
        text = (response.text or "").strip()
        if not text:
            raise LLMError("Resposta vazia do Gemini.")
        return {
            "text": text,
            "grounding_sources": _extract_grounding_sources(response),
        }
    except Exception as e:  # SDK encapsula erros em classes internas
        raise LLMError(f"Falha ao chamar Gemini: {e}") from e


def _extract_grounding_sources(response: Any) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if not grounding_metadata:
            continue
        chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            uri = getattr(web, "uri", "") or ""
            title = getattr(web, "title", "") or "Fonte web"
            if uri:
                sources.append({"title": title, "url": uri})

    # remove duplicadas preservando ordem
    unique: List[Dict[str, str]] = []
    seen = set()
    for source in sources:
        if source["url"] in seen:
            continue
        seen.add(source["url"])
        unique.append(source)

    return unique


def require_json(text: str) -> Dict[str, Any]:
    """Extract JSON object from a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("O modelo não retornou JSON.")
    raw = text[start : end + 1]
    try:
        return json.loads(raw)
    except Exception as e:
        raise LLMError(f"JSON inválido do modelo: {e}") from e
