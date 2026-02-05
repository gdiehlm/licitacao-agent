
import json, os, requests
from typing import Dict, List

OLLAMA_URL = os.environ.get("OLLAMA_URL","http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL","qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT","600"))

MASTER_SYSTEM_PROMPT = """
Você é um especialista em licitações públicas brasileiras e especificações técnicas.
Sua função é transformar uma referência comercial em uma ESPECIFICAÇÃO TÉCNICA NEUTRA,
adequada para pregão eletrônico.

REGRAS OBRIGATÓRIAS:
- É terminantemente proibido citar marcas, modelos, linhas, SKUs ou fabricantes.
- Gere apenas requisitos mínimos, objetivos e mensuráveis.
- Sempre aceite produtos equivalentes ou superiores.
- Use linguagem técnica, clara e auditável.
- Organize a resposta em blocos técnicos adequados ao tipo do item.
- Não invente requisitos sem base técnica.
- Quando houver incerteza, declare em 'assuncoes'.
"""

def call_llm(messages: List[Dict]) -> Dict:
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2}
        },
        timeout=OLLAMA_TIMEOUT
    )
    r.raise_for_status()
    content = r.json()["message"]["content"]
    start = content.find("{")
    end = content.rfind("}")
    return json.loads(content[start:end+1])

def build_spec(item_ref: str, price: float, evidences: List[Dict]) -> Dict:
    messages = [
        {"role":"system","content":MASTER_SYSTEM_PROMPT},
        {"role":"user","content":json.dumps({
            "referencia_comercial": item_ref,
            "preco_unitario": price,
            "evidencias": evidences,
            "formato_saida": {
                "descricao_resumida": "string",
                "blocos": {"Nome do bloco": ["requisito"]},
                "assuncoes": []
            }
        }, ensure_ascii=False)}
    ]
    return call_llm(messages)
