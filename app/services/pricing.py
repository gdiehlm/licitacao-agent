import re
from statistics import mean
from typing import Dict, List

import requests

PRICE_RE = re.compile(r"R\$\s*([0-9\.]+)(?:,([0-9]{2}))?", re.IGNORECASE)


def _brl_to_float(inteiro: str, centavos: str | None) -> float:
    centavos = centavos or "00"
    return float(f"{inteiro.replace('.', '')}.{centavos}")


def _extract_prices(text: str) -> List[float]:
    values: List[float] = []
    for inteiro, centavos in PRICE_RE.findall(text or ""):
        values.append(_brl_to_float(inteiro, centavos))
    return values


def estimate_price_from_licitacon(item_ref: str, searxng_url: str, min_samples: int = 3) -> Dict:
    query = f'site:licitacon {item_ref} "R$"'
    response = requests.get(
        f"{searxng_url.rstrip('/')}/search",
        params={"q": query, "format": "json", "language": "pt-BR"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    samples: List[float] = []
    sources: List[Dict[str, str]] = []

    for result in payload.get("results", []):
        text = " ".join(
            [
                str(result.get("title") or ""),
                str(result.get("content") or ""),
                str(result.get("url") or ""),
            ]
        )
        prices = _extract_prices(text)
        if not prices:
            continue
        samples.append(prices[0])
        sources.append({"title": result.get("title") or "LicitaCon", "url": result.get("url") or ""})

    if len(samples) < min_samples:
        raise ValueError(
            f"LicitaCon retornou apenas {len(samples)} preço(s) para '{item_ref}'. São necessários ao menos {min_samples} itens similares."
        )

    trimmed = samples[:min_samples]
    return {
        "average": round(mean(trimmed), 2),
        "samples": trimmed,
        "sources": sources[:min_samples],
    }
