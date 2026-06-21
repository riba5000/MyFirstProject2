"""Tests for travelpayouts_client._parse_offers — pure, no network."""
from datetime import date
from decimal import Decimal

from models import TripQuery
from travelpayouts_client import _parse_offers


def _query(pax: int = 2) -> TripQuery:
    return TripQuery(
        origem="FLN",
        destino="BKK",
        embarque=date(2026, 12, 13),
        retorno=date(2027, 1, 2),
        pax=pax,
    )


_SAMPLE_ITEM = {
    "origin": "FLN",
    "destination": "BKK",
    "price": 5200,
    "airline": "QR",
    "transfers": 1,
    "return_transfers": 2,
    "duration_to": 1800,
    "duration_back": 1920,
    "departure_at": "2026-12-13T20:00:00-03:00",
    "return_at": "2027-01-02T10:00:00+07:00",
}


def test_parse_single_offer_fields():
    offers = _parse_offers([_SAMPLE_ITEM], _query(pax=2))
    assert len(offers) == 1
    o = offers[0]
    assert o.preco_por_pax == Decimal("5200")
    assert o.preco_total == Decimal("10400.00")  # price * pax
    assert o.cias == ["QR"]
    assert o.escalas_ida == 1
    assert o.escalas_volta == 2
    assert o.duracao_ida_min == 1800
    assert o.duracao_volta_min == 1920


def test_parse_preco_por_pax_is_per_adult():
    # Premissa central: price é por adulto → total escala com pax
    o1 = _parse_offers([_SAMPLE_ITEM], _query(pax=1))[0]
    o2 = _parse_offers([_SAMPLE_ITEM], _query(pax=2))[0]
    assert o1.preco_por_pax == o2.preco_por_pax == Decimal("5200")
    assert o2.preco_total == o1.preco_total * 2


def test_parse_empty_data():
    assert _parse_offers([], _query()) == []


def test_parse_skips_items_without_price():
    item = dict(_SAMPLE_ITEM)
    item["price"] = None
    assert _parse_offers([item], _query()) == []


def test_parse_handles_missing_optional_fields():
    item = {"price": 4000}  # sem airline/transfers/duração
    o = _parse_offers([item], _query())[0]
    assert o.cias == []
    assert o.escalas_ida == 0
    assert o.escalas_volta == 0
    assert o.duracao_ida_min == 0
    assert o.duracao_volta_min == 0


def test_parse_multiple_items():
    items = [dict(_SAMPLE_ITEM, price=5000), dict(_SAMPLE_ITEM, price=6000)]
    offers = _parse_offers(items, _query())
    assert [o.preco_por_pax for o in offers] == [Decimal("5000"), Decimal("6000")]
