"""Tests for gf_search_client — puros, sem rede.

Cobrem principalmente as três armadilhas documentadas no módulo:
prefixo de moeda mentiroso, resposta vazia ambígua e volta indisponível.
"""
from datetime import date
from decimal import Decimal

import httpx
import pytest

import config
from gf_search_client import (
    _extrair_preco,
    _faixa_plausivel_brl,
    _forcar_locale_br,
    _normalizar_numero,
    _parse_offers,
)
from models import TripQuery


def _query(pax: int = 2) -> TripQuery:
    return TripQuery(
        origem="FLN", destino="BKK",
        embarque=date(2026, 12, 14), retorno=date(2027, 1, 5),
        pax=pax,
    )


_ITEM = {
    "airlines": ["LATAM", "Qatar Airways"],
    "price": "TWD 12400",
    "stops": 2,
    "segments": [
        {"from": "FLN", "to": "GRU", "duration_min": 90, "plane": "A320"},
        {"from": "GRU", "to": "DOH", "duration_min": 810, "plane": "B789"},
        {"from": "DOH", "to": "BKK", "duration_min": 380, "plane": "A350"},
    ],
    "source": "gf_search",
}


# ── normalização de número (locale pt-BR vs en-US) ────────────────────────────

@pytest.mark.parametrize("txt,esperado", [
    ("12345", "12345"),
    ("12.345", "12345"),          # pt-BR milhar
    ("1.234.567", "1234567"),     # pt-BR milhar duplo
    ("12.345,67", "12345.67"),    # pt-BR completo
    ("1,234.56", "1234.56"),      # en-US completo
    ("12,50", "12.50"),           # vírgula decimal
    ("12.34", "12.34"),           # ponto decimal
])
def test_normalizar_numero(txt, esperado):
    assert _normalizar_numero(txt) == Decimal(esperado)


def test_normalizar_numero_vazio():
    assert _normalizar_numero("") is None
    assert _normalizar_numero("abc") is None


# ── armadilha 1: o prefixo "TWD" é colado e não indica a moeda real ───────────

def test_extrai_valor_ignorando_prefixo_mentiroso():
    assert _extrair_preco("TWD 12400") == Decimal("12400")


def test_extrai_valor_com_simbolo_brl():
    assert _extrair_preco("R$ 12.400,50") == Decimal("12400.50")


def test_extrai_valor_numerico():
    assert _extrair_preco(12400) == Decimal("12400")


def test_extrai_preco_ausente_ou_vazio():
    assert _extrair_preco(None) is None
    assert _extrair_preco("") is None
    assert _extrair_preco("TWD 0") is None


def test_faixa_plausivel_brl():
    assert _faixa_plausivel_brl(Decimal("12400")) is True
    assert _faixa_plausivel_brl(Decimal("300")) is False        # baixo demais
    assert _faixa_plausivel_brl(Decimal("90000")) is False      # provável TWD


def test_avisa_quando_preco_parece_outra_moeda(caplog):
    caro = dict(_ITEM, price="TWD 250000")   # típico de valor não convertido
    _parse_offers([caro], _query())
    assert "moeda" in caplog.text.lower()


# ── parsing geral ─────────────────────────────────────────────────────────────

def test_parse_campos_basicos():
    o = _parse_offers([_ITEM], _query(pax=2))[0]
    assert o.preco_total == Decimal("12400")
    assert o.preco_por_pax == Decimal("6200.00")
    assert o.cias == ["LATAM", "Qatar Airways"]
    assert o.escalas_ida == 2
    assert o.duracao_ida_min == 1280          # 90 + 810 + 380


# ── armadilha 3: a volta não é confiável → None, nunca zero ───────────────────

def test_volta_fica_desconhecida():
    o = _parse_offers([_ITEM], _query())[0]
    assert o.escalas_volta is None
    assert o.duracao_volta_min is None


def test_preco_como_por_passageiro(monkeypatch):
    monkeypatch.setattr(config, "PRECO_E_TOTAL", False)
    o = _parse_offers([_ITEM], _query(pax=2))[0]
    assert o.preco_por_pax == Decimal("12400")
    assert o.preco_total == Decimal("24800.00")


def test_ignora_item_sem_preco():
    """Itens de source='jx_static' costumam vir sem preço e não servem p/ alerta."""
    sem_preco = dict(_ITEM, price="", source="jx_static")
    assert _parse_offers([sem_preco], _query()) == []


def test_lista_vazia():
    assert _parse_offers([], _query()) == []


def test_respeita_max_ofertas(monkeypatch):
    monkeypatch.setattr(config, "MAX_OFERTAS_POR_QUERY", 2)
    itens = [dict(_ITEM, price=f"TWD {12000 + i}") for i in range(5)]
    assert len(_parse_offers(itens, _query())) == 2


def test_item_sem_segmentos_nao_quebra():
    magro = {"price": "TWD 9000", "stops": 1}
    o = _parse_offers([magro], _query())[0]
    assert o.duracao_ida_min == 0
    assert o.cias == []


# ── injeção de locale (para o preço vir em BRL) ───────────────────────────────

def test_forcar_locale_injeta_brl_e_restaura(monkeypatch):
    capturado = {}

    def fake_get(self, url, *args, **kwargs):
        capturado["params"] = kwargs.get("params")
        return "resp"

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    original = httpx.Client.get

    with _forcar_locale_br():
        httpx.Client.get(httpx.Client(), "https://www.google.com/travel/flights/search",
                         params={"tfs": "abc", "hl": "zh-TW"})

    assert capturado["params"]["curr"] == "BRL"
    assert capturado["params"]["gl"] == "BR"
    assert capturado["params"]["hl"] == "pt-BR"      # sobrescreve o zh-TW da lib
    assert capturado["params"]["tfs"] == "abc"       # preserva o resto
    assert httpx.Client.get is original              # patch revertido


def test_forcar_locale_nao_toca_outras_urls(monkeypatch):
    capturado = {}

    def fake_get(self, url, *args, **kwargs):
        capturado["params"] = kwargs.get("params")
        return "resp"

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with _forcar_locale_br():
        httpx.Client.get(httpx.Client(), "https://exemplo.com/api", params={"a": "1"})

    assert capturado["params"] == {"a": "1"}
