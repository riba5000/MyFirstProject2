"""
Cliente do SerpApi — engine `google_flights`.

Endpoint: GET https://serpapi.com/search?engine=google_flights
Doc: https://serpapi.com/google-flights-api

Por que esta fonte (agosto/2026):
  - A Amadeus Self-Service foi desativada em 17/07/2026 (novos cadastros fechados
    e chaves desligadas), então deixou de ser opção.
  - A Travelpayouts/Aviasales gratuita só tem cache de 48h → nada para datas futuras.
  - O SerpApi devolve o resultado REAL do Google Flights, inclusive para datas
    distantes. Custo: cota apertada (250 buscas/mês no gratuito) — ver quota.py.

LIMITAÇÕES CONHECIDAS (deliberadas, para não gastar cota em dobro):
  - Numa busca round-trip, cada item de `best_flights`/`other_flights` traz o
    PREÇO TOTAL da ida-e-volta, mas os segmentos (`flights`) são só os da IDA.
    Os detalhes da volta exigiriam uma 2ª chamada com `departure_token`, o que
    dobraria o consumo. Por isso `escalas_volta` e `duracao_volta_min` ficam None.

PREMISSA DE PREÇO:
  O Google Flights mostra o preço total da viagem para o nº de passageiros
  pesquisado. Logo, por padrão tratamos `price` como TOTAL do grupo:
      preco_total   = price
      preco_por_pax = price / pax
  Se na verificação os números vierem pela metade/dobro do esperado, basta
  inverter com PRECO_E_TOTAL=false no .env — sem mexer no código.
"""
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import httpx

import config
from models import FareOffer, TripQuery

logger = logging.getLogger(__name__)

URL = "https://serpapi.com/search"

# Já avisamos sobre a interpretação do preço nesta execução?
_avisou_preco = False


def _cias_do_itinerario(item: dict) -> list[str]:
    """Nomes de cia (sem repetir, preservando a ordem dos segmentos)."""
    vistas: list[str] = []
    for seg in item.get("flights", []):
        nome = seg.get("airline")
        if nome and nome not in vistas:
            vistas.append(nome)
    return vistas


def _parse_offers(body: dict, query: TripQuery) -> list[FareOffer]:
    """Converte a resposta do SerpApi em FareOffer. Puro — testável sem rede."""
    global _avisou_preco
    now = datetime.now(timezone.utc)
    offers: list[FareOffer] = []

    itens = list(body.get("best_flights", [])) + list(body.get("other_flights", []))

    for item in itens[: config.MAX_OFERTAS_POR_QUERY]:
        preco_bruto = item.get("price")
        if preco_bruto is None:
            continue

        bruto = Decimal(str(preco_bruto))
        if config.PRECO_E_TOTAL:
            preco_total = bruto
            preco_por_pax = (bruto / query.pax).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            preco_por_pax = bruto
            preco_total = (bruto * query.pax).quantize(Decimal("0.01"), ROUND_HALF_UP)

        if not _avisou_preco:
            _avisou_preco = True
            logger.info(
                "Interpretação de preço: bruto=%s para %d pax → total=%s, por pax=%s "
                "(inverta com PRECO_E_TOTAL no .env se estiver trocado)",
                bruto, query.pax, preco_total, preco_por_pax,
            )

        segmentos = item.get("flights", [])
        offers.append(
            FareOffer(
                query=query,
                preco_total=preco_total,
                preco_por_pax=preco_por_pax,
                cias=_cias_do_itinerario(item),
                escalas_ida=max(0, len(segmentos) - 1),
                escalas_volta=None,          # ver LIMITAÇÕES no topo do módulo
                duracao_ida_min=int(item.get("total_duration", 0) or 0),
                duracao_volta_min=None,
                coletado_em=now,
            )
        )

    return offers


def flight_offers_search(query: TripQuery) -> list[FareOffer]:
    if not config.SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY não configurada no .env")

    params = {
        "engine": "google_flights",
        "departure_id": query.origem,
        "arrival_id": query.destino,
        "outbound_date": query.embarque.isoformat(),
        "return_date": query.retorno.isoformat(),
        "type": "1",                      # 1 = ida e volta
        "adults": str(query.pax),
        "currency": config.MOEDA,
        "hl": "pt-br",
        "gl": "br",
        "api_key": config.SERPAPI_KEY,
    }
    if config.NONSTOP_ONLY:
        params["stops"] = "1"             # 1 = somente voo direto

    resp = httpx.get(URL, params=params, timeout=60)

    if resp.status_code == 429:
        logger.warning("Rate limit do SerpApi; aguardando 10s")
        time.sleep(10)
        return flight_offers_search(query)

    if resp.status_code == 401:
        raise RuntimeError("SerpApi recusou a chave (401). Confira SERPAPI_KEY no .env")

    if resp.status_code >= 400:
        logger.error("HTTP %s do SerpApi: %s", resp.status_code, resp.text[:300])
        resp.raise_for_status()

    body = resp.json()

    # O SerpApi devolve 200 + campo "error" quando o Google não achou nada
    if body.get("error"):
        logger.info("Sem resultados para %s→%s %s: %s",
                    query.origem, query.destino, query.embarque, body["error"])
        return []

    return _parse_offers(body, query)
