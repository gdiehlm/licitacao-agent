import re
from dataclasses import dataclass
from typing import List, Optional

MONEY_RE = re.compile(r"R\$\s*([0-9\.]+)(?:,([0-9]{2}))?")
# captura "20 unidades do X ... no preço de R$ 400,00"
ITEM_RE = re.compile(
    r"(\d+)\s*(unidades?|caixas?)\s+(?:do|de)\s+(.+?)(?:\s+no\s+pre[cç]o\s+de\s+R\$\s*[^\.;]+|\.|$)",
    re.IGNORECASE
)

@dataclass
class ParsedItem:
    prioridade: int
    referencia_raw: str
    quantidade: int
    unidade: str
    preco_unit: float

def _parse_money(text: str) -> Optional[float]:
    m = MONEY_RE.search(text)
    if not m:
        return None
    inteiro = m.group(1).replace(".", "")
    cent = m.group(2) or "00"
    return float(f"{inteiro}.{cent}")

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
        price = _parse_money(part) or 0.0

        items.append(ParsedItem(
            prioridade=prioridade,
            referencia_raw=ref,
            quantidade=qty,
            unidade=unidade,
            preco_unit=price
        ))
        prioridade += 1

    if not items:
        raise ValueError("Não consegui identificar itens. Use: 'N unidades/caixas de ... no preço de R$ X,XX cada.'")
    return items
