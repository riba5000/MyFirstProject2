"""
Cliente da Travelpayouts / Aviasales Data API (fonte alternativa ao Amadeus).

Endpoint: GET {BASE}/aviasales/v3/prices_for_dates
Doc: https://support.travelpayouts.com/hc/en-us/articles/203956163-Aviasales-Data-API

Diferenças vs. Amadeus:
  - Sem OAuth: o token vai no header `X-Access-Token` (não precisa cachear token).
  - Os preços vêm de CACHE (buscas reais recentes no Aviasales), não de busca ao vivo.
    Combinações de data muito específicas podem voltar vazias — é esperado.

PREMISSA DE PREÇO (importante para o alerta):
  Na v3 `prices_for_dates`, o campo `price` é a tarifa para UM adulto.
  Logo: preco_por_pax = price  e  preco_total = price * pax.
  Se a doc/contrato mudar para "preço total", inverter aqui.
"""
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

import config
from models import FareOffer, TripQuery

logger = logging.getLogger(__name__)


def _parse_offers(data: list[dict], query: TripQuery) -> list[FareOffer]:
    """Converte a lista `data` da resposta em FareOffer. Função pura (testável sem rede)."""
    now = datetime.now(timezone.utc)
    offers: list[FareOffer] = []

    for item in data:
        if item.get("price") is None:
            continue

        preco_por_pax = Decimal(str(item["price"]))
        preco_total = (preco_por_pax * query.pax).quantize(Decimal("0.01"))

        airline = item.get("airline")
        cias = [airline] if airline else []

        offers.append(
            FareOffer(
                query=query,
                preco_total=preco_total,
                preco_por_pax=preco_por_pax,
                cias=cias,
                escalas_ida=int(item.get("transfers", 0) or 0),
                escalas_volta=int(item.get("return_transfers", 0) or 0),
                duracao_ida_min=int(item.get("duration_to", 0) or 0),
                duracao_volta_min=int(item.get("duration_back", 0) or 0),
                coletado_em=now,
            )
        )

    return offers


def flight_offers_search(query: TripQuery) -> list[FareOffer]:
    if not config.TRAVELPAYOUTS_TOKEN:
        raise RuntimeError("TRAVELPAYOUTS_TOKEN não configurado no .env")

    params: dict = {
        "origin": query.origem,
        "destination": query.destino,
        "departure_at": query.embarque.isoformat(),
        "return_at": query.retorno.isoformat(),
        "currency": config.MOEDA.lower(),
        "sorting": "price",
        "one_way": "false",
        "unique": "false",
        "limit": str(config.MAX_OFERTAS_POR_QUERY),
        "direct": "true" if config.NONSTOP_ONLY else "false",
    }

    resp = httpx.get(
        f"{config.TRAVELPAYOUTS_BASE_URL}/aviasales/v3/prices_for_dates",
        params=params,
        headers={"X-Access-Token": config.TRAVELPAYOUTS_TOKEN},
        timeout=20,
    )

    if resp.status_code == 429:
        logger.warning("Rate-limited pela Travelpayouts; aguardando 5s")
        time.sleep(5)
        return flight_offers_search(query)

    resp.raise_for_status()
    body = resp.json()

    if not body.get("success", False):
        logger.warning("Resposta sem sucesso para %s→%s: %s",
                       query.origem, query.destino, body.get("error"))
        return []

    return _parse_offers(body.get("data", []), query)
