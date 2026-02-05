import os
import json
import requests
from typing import Any, Dict, List

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

class LLMError(RuntimeError):
    pass

def ollama_chat(messages: List[Dict[str,str]]) -> str:
    """Call Ollama /api/chat and return assistant content."""
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}) or {}
        content = msg.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise LLMError("Resposta vazia do modelo")
        return content
    except requests.RequestException as e:
        raise LLMError(f"Falha ao chamar Ollama: {e}") from e

def require_json(text: str) -> Dict[str, Any]:
    """Extract JSON object from a model response."""
    # Try direct
    text = text.strip()
    # remove code fences
    if text.startswith("```"):
        text = text.strip("`")
    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("O modelo não retornou JSON.")
    raw = text[start:end+1]
    try:
        return json.loads(raw)
    except Exception as e:
        raise LLMError(f"JSON inválido do modelo: {e}") from e
