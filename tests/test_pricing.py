"""Tests for pricing.py — pure, no network."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from models import FareOffer, TripQuery
from pricing import _percentil, avaliar_alertas, melhor_por_rota


def _make_offer(
    destino: str = "BKK",
    preco_pax: float = 5000.0,
    embarque: date = date(2026, 12, 13),
    retorno: date = date(2027, 1, 2),
) -> FareOffer:
    return FareOffer(
        query=TripQuery(
            origem="FLN",
            destino=destino,
            embarque=embarque,
            retorno=retorno,
            pax=2,
        ),
        preco_total=Decimal(str(preco_pax * 2)),
        preco_por_pax=Decimal(str(preco_pax)),
        cias=["LA"],
        escalas_ida=1,
        escalas_volta=1,
        duracao_ida_min=900,
        duracao_volta_min=920,
        coletado_em=datetime.now(timezone.utc),
    )


# --- _percentil ---

def test_percentil_single_value():
    assert _percentil([Decimal("100")], 10) == Decimal("100")


def test_percentil_even_split():
    vals = [Decimal(str(i)) for i in range(1, 101)]
    p50 = _percentil(vals, 50)
    assert 49 <= float(p50) <= 51


def test_percentil_p10():
    vals = [Decimal(str(i)) for i in range(1, 101)]
    p10 = _percentil(vals, 10)
    assert float(p10) < 15


def test_percentil_empty_raises():
    with pytest.raises(ValueError):
        _percentil([], 10)


# --- melhor_por_rota ---

def test_melhor_por_rota_single():
    o = _make_offer("BKK", 5000)
    assert melhor_por_rota([o]) == {("FLN", "BKK"): o}


def test_melhor_por_rota_picks_cheapest():
    cheap = _make_offer("BKK", 4000)
    expensive = _make_offer("BKK", 7000)
    result = melhor_por_rota([expensive, cheap])
    assert result[("FLN", "BKK")] is cheap


def test_melhor_por_rota_multiple_routes():
    bkk = _make_offer("BKK", 5000)
    sgn = _make_offer("SGN", 4500)
    result = melhor_por_rota([bkk, sgn])
    assert result[("FLN", "BKK")] is bkk
    assert result[("FLN", "SGN")] is sgn


def test_melhor_por_rota_empty():
    assert melhor_por_rota([]) == {}


# --- avaliar_alertas ---

def test_alerta_hard_target_triggered():
    offer = _make_offer("BKK", 6000.0)  # below 6500 target
    alertas = avaliar_alertas([offer], [])
    assert len(alertas) == 1
    assert alertas[0][1] == "hard_target"


def test_alerta_hard_target_not_triggered():
    offer = _make_offer("BKK", 7000.0)  # above 6500
    alertas = avaliar_alertas([offer], [])
    assert alertas == []


def test_alerta_p10_not_triggered_shallow_history():
    # Only 9 historical points — too shallow for P10 alert
    historico = [_make_offer("BKK", 7000 + i * 10) for i in range(9)]
    offer = _make_offer("BKK", 6600.0)  # below hard target? no (6600 > 6500); above P10?
    alertas = avaliar_alertas([offer], historico)
    # 9 < 10 items, no p10 alert
    assert alertas == []


def test_alerta_p10_triggered_with_mature_history():
    # 20 historical offers all at ~8000, current at 6600 — should be way below P10
    historico = [_make_offer("BKK", 8000 + i * 10) for i in range(20)]
    offer = _make_offer("BKK", 6600.0)  # above 6500 hard target but below P10 of ~8000
    alertas = avaliar_alertas([offer], historico)
    assert len(alertas) == 1
    assert alertas[0][1] == "p10_historico"


def test_alerta_no_double_trigger():
    # If hard_target fires, p10 branch is skipped (continue after first match)
    historico = [_make_offer("BKK", 8000 + i * 10) for i in range(20)]
    offer = _make_offer("BKK", 5000.0)  # triggers hard_target
    alertas = avaliar_alertas([offer], historico)
    reasons = [r for _, r in alertas]
    assert reasons.count("hard_target") == 1
    # Should not also appear as p10_historico
    assert "p10_historico" not in reasons


def test_alerta_multiple_routes_independent():
    bkk_cheap = _make_offer("BKK", 5000)   # triggers hard_target
    sgn_normal = _make_offer("SGN", 9000)   # no alert
    alertas = avaliar_alertas([bkk_cheap, sgn_normal], [])
    assert len(alertas) == 1
    assert alertas[0][0].query.destino == "BKK"
