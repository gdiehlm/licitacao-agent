import json
from typing import Dict

from services.llm_client import LLMError, gemini_chat, require_json

MASTER_SYSTEM_PROMPT = """
Você é um especialista em licitações públicas brasileiras e elaboração de especificações técnicas.
Sua saída deve estar alinhada à Lei 14.133/2021, com neutralidade e segurança jurídica.

REGRAS OBRIGATÓRIAS:
- Proibido citar marcas, modelos, linhas, SKUs ou fabricantes.
- Descrever requisitos mínimos por desempenho, funcionalidade e critérios mensuráveis.
- Linguagem formal administrativa.
- Evitar qualquer termo que possa caracterizar direcionamento.
- Sempre considerar possibilidade de equivalente técnico.
- Incluir normas técnicas aplicáveis (ABNT, ISO, INMETRO ou equivalentes), quando pertinente.
- Quando houver incerteza, registrar em 'assumptions'.

Retorne SOMENTE JSON válido no formato solicitado.
"""


def build_spec(item_ref: str, price: float) -> Dict:
    messages = [
        {"role": "system", "content": MASTER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "referencia_comercial": item_ref,
                    "preco_unitario_estimado": price,
                    "objetivo": "Gerar especificação técnica neutra para termo de referência de licitação pública.",
                    "formato_saida": {
                        "categoria": "string",
                        "resumo": "string",
                        "detalhada": "string",
                        "assumptions": ["string"],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]

    result = gemini_chat(messages, enable_google_grounding=True)
    payload = require_json(result["text"])

    if "sources" not in payload:
        payload["sources"] = result.get("grounding_sources", [])

    required_fields = ["categoria", "resumo", "detalhada"]
    for field in required_fields:
        if field not in payload:
            raise LLMError(f"Campo obrigatório ausente na resposta da IA: {field}")

    payload.setdefault("assumptions", [])
    payload.setdefault("sources", [])
    return payload
