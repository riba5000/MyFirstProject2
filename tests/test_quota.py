"""Tests for quota.py — a trava que evita estourar a cota do SerpApi."""
from datetime import datetime, timezone

import pytest

import quota


@pytest.fixture(autouse=True)
def _quota_isolada(tmp_path, monkeypatch):
    monkeypatch.setattr(quota, "QUOTA_PATH", tmp_path / "q.json")
    yield


_AGO = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
_SET = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def test_chave_mes_formato():
    assert quota._chave_mes(_AGO) == "2026-08"
    assert quota._chave_mes(datetime(2027, 1, 5)) == "2027-01"


def test_pode_consultar_cabe():
    assert quota.pode_consultar(usado=100, a_consultar=6, limite=250) is True


def test_pode_consultar_exatamente_no_limite():
    assert quota.pode_consultar(usado=244, a_consultar=6, limite=250) is True


def test_pode_consultar_estoura():
    assert quota.pode_consultar(usado=245, a_consultar=6, limite=250) is False


def test_uso_inicial_zero():
    assert quota.uso_do_mes(_AGO) == 0


def test_registrar_e_acumular():
    quota.registrar_uso(_AGO)
    quota.registrar_uso(_AGO, 5)
    assert quota.uso_do_mes(_AGO) == 6


def test_contador_reseta_por_mes():
    quota.registrar_uso(_AGO, 200)
    assert quota.uso_do_mes(_SET) == 0
    assert quota.uso_do_mes(_AGO) == 200


def test_arquivo_corrompido_nao_quebra():
    quota.QUOTA_PATH.write_text("{lixo!!", encoding="utf-8")
    assert quota.uso_do_mes(_AGO) == 0


def test_persiste_entre_leituras():
    quota.registrar_uso(_AGO, 3)
    assert quota._ler() == {"2026-08": 3}
