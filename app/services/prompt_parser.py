import re
from dataclasses import dataclass
from typing import List

# captura "20 unidades do X" ou "20 unidades de X"
ITEM_RE = re.compile(
    r"(\d+)\s*(unidades?|caixas?)\s+(?:do|de)\s+(.+?)(?:\.|$)",
    re.IGNORECASE
)

@dataclass
class ParsedItem:
    prioridade: int
    referencia_raw: str
    quantidade: int
    unidade: str
    preco_unit: float = 0.0

def parse_prompt(prompt: str) -> List[ParsedItem]:
    parts = re.split(r"[\n;]+", prompt)
    items: List[ParsedItem] = []
    prioridade = 1

    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = ITEM_RE.search(part)
        if not m:
            continue
        qty = int(m.group(1))
        unidade_raw = m.group(2).lower()
        ref = m.group(3).strip().rstrip(".")
        unidade = "UND" if "unidad" in unidade_raw else "CX" if "caix" in unidade_raw else unidade_raw.upper()
        items.append(ParsedItem(
            prioridade=prioridade,
            referencia_raw=ref,
            quantidade=qty,
            unidade=unidade,
            preco_unit=0.0
        ))
        prioridade += 1

    if not items:
        raise ValueError("Não consegui identificar itens. Use: 'N unidades/caixas de ...'.")
    return items
