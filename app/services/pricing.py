import json
from statistics import mean
from typing import Dict, List

from services.llm_client import gemini_chat, require_json


def estimate_price_from_licitacon(item_ref: str, min_samples: int = 3) -> Dict:
    """
    Usa Google Search Grounding (Gemini) para buscar preços públicos no contexto do LicitaCon
    e retorna média com amostras auditáveis.
    """
    prompt = {
        "tarefa": "Pesquisar preços públicos para referência de compra governamental",
        "restricoes": [
            "priorizar resultados de LicitaCon e portais públicos de compras",
            "retornar valores numéricos em BRL",
            "não inventar preços",
            "se não houver evidência suficiente, retornar lista vazia",
        ],
        "item": item_ref,
        "minimo_amostras": min_samples,
        "formato_saida": {
            "samples": [12.34],
            "sources": [{"title": "string", "url": "string"}],
        },
    }

    messages = [
        {
            "role": "system",
            "content": "Retorne apenas JSON válido conforme solicitado.",
        },
        {
            "role": "user",
            "content": json.dumps(prompt, ensure_ascii=False),
        },
    ]

    result = gemini_chat(messages, enable_google_grounding=True)
    payload = require_json(result["text"])

    samples_raw = payload.get("samples", [])
    samples: List[float] = []
    for value in samples_raw:
        try:
            samples.append(float(value))
        except (TypeError, ValueError):
            continue

    if len(samples) < min_samples:
        raise ValueError(
            f"Google Search Grounding retornou apenas {len(samples)} preço(s) para '{item_ref}'. São necessários ao menos {min_samples} itens similares."
        )

    trimmed = samples[:min_samples]

    sources = payload.get("sources") or result.get("grounding_sources", [])

    return {
        "average": round(mean(trimmed), 2),
        "samples": trimmed,
        "sources": sources[:min_samples],
    }
