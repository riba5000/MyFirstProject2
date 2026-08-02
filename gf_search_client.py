"""
Cliente da biblioteca `gf_search` (pacote PyPI: google-flights-search).

Fala com o Google Flights via SSR (sem navegador, sem chave, SEM COTA), o que
permite rodar a grade inteira todo dia em vez de uma amostra. Foi escolhida
por tratar aeroportos regionais//de baixo tráfego — o caso do FLN, onde a
`fast-flights` retorna vazio silenciosamente.

    gf_search.search(origin, destination, departure_date, return_date=None,
                     adults=1, travel_class="economy", max_results=5) -> list[dict]

    item = {"airlines": [...], "price": "TWD 12345", "stops": int,
            "segments": [{"from","to","departure","arrival","duration_min","plane"}],
            "source": "gf_search" | "jx_static"}

TRÊS ARMADILHAS DESTA BIBLIOTECA (e como são tratadas aqui)
-----------------------------------------------------------
1) MOEDA. Ela pede `hl=zh-TW` fixo e monta o preço como f"TWD {valor}" —
   o prefixo é COLADO no número, não reflete a moeda real. Portanto o rótulo
   é ignorado aqui. Para o número sair em BRL, `_forcar_locale_br()` injeta
   curr/gl/hl na requisição. Como isso depende de internals da lib, existe
   ainda uma checagem de ordem de grandeza (`_faixa_plausivel_brl`) que grita
   no log se os valores parecerem de outra moeda.

2) FALHA SILENCIOSA. A lib devolve [] tanto para "rota sem voos" quanto para
   erro de rede. Aqui a diferença é registrada no log pelo chamador; este
   módulo só sinaliza quantos itens vieram e se algum foi descartado.

3) VOLTA. Não há separação confiável entre os segmentos de ida e de volta na
   resposta, então `escalas_volta`/`duracao_volta_min` ficam None em vez de
   receberem um zero que seria mentira. `stops` é usado como escalas da ida.
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx

import config
from models import FareOffer, TripQuery

logger = logging.getLogger(__name__)

# Injetado na requisição para o Google devolver valores em BRL.
_LOCALE_BR = {"curr": "BRL", "gl": "BR", "hl": "pt-BR"}

# Faixa de plausibilidade do preço TOTAL da viagem, em BRL. Serve só para
# detectar que a moeda veio errada (TWD, por exemplo, seria ~5x maior).
_BRL_MIN = Decimal("800")
_BRL_MAX = Decimal("80000")


@contextmanager
def _forcar_locale_br():
    """
    Faz a `gf_search` pedir preços em BRL.

    A lib fixa `hl=zh-TW` num dicionário interno e não expõe configuração, então
    interceptamos httpx.Client.get e sobrescrevemos os parâmetros de locale só
    nas chamadas ao Google Flights. O patch é revertido no finally.
    """
    original = httpx.Client.get

    def _get(self, url, *args, **kwargs):
        if "travel/flights" in str(url):
            params = dict(kwargs.get("params") or {})
            params.update(_LOCALE_BR)
            kwargs["params"] = params
        return original(self, url, *args, **kwargs)

    httpx.Client.get = _get
    try:
        yield
    finally:
        httpx.Client.get = original


def _normalizar_numero(txt: str) -> Decimal | None:
    """
    '12.345' → 12345 | '12.345,67' → 12345.67 | '1,234.56' → 1234.56 | '12345' → 12345

    Assume pt-BR (ponto = milhar) quando houver ambiguidade, já que forçamos
    esse locale — mas trata o formato en-US também, por segurança.
    """
    s = re.sub(r"[^\d.,]", "", txt or "")
    if not s:
        return None

    tem_ponto, tem_virgula = "." in s, "," in s
    if tem_ponto and tem_virgula:
        # o separador mais à direita é o decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif tem_virgula:
        partes = s.split(",")
        s = s.replace(",", ".") if len(partes) == 2 and len(partes[1]) == 2 else s.replace(",", "")
    elif tem_ponto:
        partes = s.split(".")
        # "12.345" ou "1.234.567" → milhar; "12.34" → decimal
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            s = s.replace(".", "")

    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _extrair_preco(bruto) -> Decimal | None:
    """
    Extrai o VALOR do campo `price`, ignorando o prefixo de moeda.

    O prefixo é sempre "TWD" nesta lib, independentemente da moeda real
    (ver armadilha nº 1 no topo), por isso não serve para nada.
    """
    if bruto is None:
        return None
    if isinstance(bruto, (int, float, Decimal)):
        return Decimal(str(bruto))
    valor = _normalizar_numero(str(bruto))
    return valor if valor and valor > 0 else None


def _faixa_plausivel_brl(valor: Decimal) -> bool:
    return _BRL_MIN <= valor <= _BRL_MAX


def _parse_offers(itens: list[dict], query: TripQuery) -> list[FareOffer]:
    """Converte a resposta da gf_search em FareOffer. Puro — testável sem rede."""
    agora = datetime.now(timezone.utc)
    offers: list[FareOffer] = []
    suspeitos = 0

    for item in itens[: config.MAX_OFERTAS_POR_QUERY]:
        valor = _extrair_preco(item.get("price"))
        if valor is None:
            continue  # itens sem preço (ex.: source="jx_static") não servem para alerta

        if config.PRECO_E_TOTAL:
            preco_total = valor
            preco_por_pax = (valor / query.pax).quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            preco_por_pax = valor
            preco_total = (valor * query.pax).quantize(Decimal("0.01"), ROUND_HALF_UP)

        if not _faixa_plausivel_brl(preco_total):
            suspeitos += 1

        segmentos = item.get("segments") or []
        duracao = sum(int(s.get("duration_min", 0) or 0) for s in segmentos)

        offers.append(
            FareOffer(
                query=query,
                preco_total=preco_total,
                preco_por_pax=preco_por_pax,
                cias=list(item.get("airlines") or []),
                escalas_ida=int(item.get("stops", 0) or 0),
                escalas_volta=None,        # ver armadilha nº 3 no topo
                duracao_ida_min=duracao,
                duracao_volta_min=None,
                coletado_em=agora,
            )
        )

    if suspeitos:
        logger.warning(
            "%d preço(s) fora da faixa esperada em BRL (R$%s–R$%s). A moeda pode "
            "não ter vindo em BRL — confira antes de confiar no alerta.",
            suspeitos, _BRL_MIN, _BRL_MAX,
        )

    return offers


def flight_offers_search(query: TripQuery) -> list[FareOffer]:
    try:
        import gf_search
    except ImportError as exc:
        raise RuntimeError(
            "Biblioteca não instalada. Rode: pip install google-flights-search"
        ) from exc

    with _forcar_locale_br():
        itens = gf_search.search(
            origin=query.origem,
            destination=query.destino,
            departure_date=query.embarque.isoformat(),
            return_date=query.retorno.isoformat(),
            adults=query.pax,
            travel_class="economy",
            max_results=config.MAX_OFERTAS_POR_QUERY,
        )

    if not itens:
        # A lib não distingue "sem voos" de "falha de rede" (armadilha nº 2)
        logger.info("Resposta vazia para %s→%s %s (rota sem voos OU falha de rede)",
                    query.origem, query.destino, query.embarque)
        return []

    return _parse_offers(itens, query)
