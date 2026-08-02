"""Tests for serpapi_client._parse_offers — pure, no network."""
from datetime import date
from decimal import Decimal

import pytest

import config
import serpapi_client
from models import TripQuery
from serpapi_client import _cias_do_itinerario, _parse_offers


@pytest.fixture(autouse=True)
def _reset_aviso():
    """O aviso de interpretação de preço é one-shot por processo."""
    serpapi_client._avisou_preco = False
    yield


def _query(pax: int = 2) -> TripQuery:
    return TripQuery(
        origem="FLN", destino="BKK",
        embarque=date(2026, 12, 14), retorno=date(2027, 1, 5),
        pax=pax,
    )


_ITEM = {
    "flights": [
        {"airline": "LATAM", "duration": 90},
        {"airline": "Qatar Airways", "duration": 700},
        {"airline": "Qatar Airways", "duration": 380},
    ],
    "layovers": [{"duration": 120, "name": "Guarulhos"}, {"duration": 90, "name": "Doha"}],
    "total_duration": 1800,
    "price": 12400,
    "type": "Round trip",
}


def _body(*itens, other=()):
    return {"best_flights": list(itens), "other_flights": list(other)}


def test_parse_campos_basicos():
    o = _parse_offers(_body(_ITEM), _query(pax=2))[0]
    assert o.preco_total == Decimal("12400")
    assert o.preco_por_pax == Decimal("6200.00")
    assert o.cias == ["LATAM", "Qatar Airways"]      # sem repetir
    assert o.escalas_ida == 2                          # 3 segmentos → 2 escalas
    assert o.duracao_ida_min == 1800


def test_volta_e_desconhecida_nao_zero():
    """Não podemos afirmar 0 escalas na volta — o dado não vem na busca inicial."""
    o = _parse_offers(_body(_ITEM), _query())[0]
    assert o.escalas_volta is None
    assert o.duracao_volta_min is None


def test_preco_como_total_do_grupo(monkeypatch):
    monkeypatch.setattr(config, "PRECO_E_TOTAL", True)
    o = _parse_offers(_body(_ITEM), _query(pax=2))[0]
    assert o.preco_total == Decimal("12400")
    assert o.preco_por_pax == Decimal("6200.00")


def test_preco_como_por_passageiro(monkeypatch):
    monkeypatch.setattr(config, "PRECO_E_TOTAL", False)
    o = _parse_offers(_body(_ITEM), _query(pax=2))[0]
    assert o.preco_por_pax == Decimal("12400")
    assert o.preco_total == Decimal("24800.00")


def test_junta_best_e_other_flights():
    outro = dict(_ITEM, price=13000)
    offers = _parse_offers(_body(_ITEM, other=[outro]), _query())
    assert [o.preco_total for o in offers] == [Decimal("12400"), Decimal("13000")]


def test_respeita_max_ofertas_por_query(monkeypatch):
    monkeypatch.setattr(config, "MAX_OFERTAS_POR_QUERY", 2)
    itens = [dict(_ITEM, price=10000 + i) for i in range(5)]
    assert len(_parse_offers(_body(*itens), _query())) == 2


def test_ignora_item_sem_preco():
    sem_preco = {k: v for k, v in _ITEM.items() if k != "price"}
    assert _parse_offers(_body(sem_preco), _query()) == []


def test_resposta_vazia():
    assert _parse_offers({}, _query()) == []


def test_voo_direto_zero_escalas():
    direto = dict(_ITEM, flights=[{"airline": "Emirates", "duration": 900}])
    o = _parse_offers(_body(direto), _query())[0]
    assert o.escalas_ida == 0


def test_cias_sem_nome_nao_quebra():
    item = dict(_ITEM, flights=[{"duration": 100}, {"airline": "GOL"}])
    assert _cias_do_itinerario(item) == ["GOL"]
