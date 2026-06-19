"""Tests for dates.py — pure, no network."""
from datetime import date, timedelta

import pytest

import config
from dates import _in_blackout, gerar_grade
from models import TripQuery


def test_in_blackout_true():
    blackout = (date(2026, 12, 20), date(2027, 1, 2))
    assert _in_blackout(date(2026, 12, 25), blackout) is True
    assert _in_blackout(date(2026, 12, 20), blackout) is True
    assert _in_blackout(date(2027, 1, 2), blackout) is True


def test_in_blackout_false():
    blackout = (date(2026, 12, 20), date(2027, 1, 2))
    assert _in_blackout(date(2026, 12, 19), blackout) is False
    assert _in_blackout(date(2027, 1, 3), blackout) is False


def test_gerar_grade_returns_list_of_trip_query():
    grade = gerar_grade()
    assert isinstance(grade, list)
    assert len(grade) > 0
    assert all(isinstance(q, TripQuery) for q in grade)


def test_gerar_grade_no_duplicates():
    grade = gerar_grade()
    keys = [(q.origem, q.destino, q.embarque, q.retorno) for q in grade]
    assert len(keys) == len(set(keys))


def test_gerar_grade_blackout_embarque_excluded():
    grade = gerar_grade()
    for q in grade:
        assert not _in_blackout(q.embarque, config.BLACKOUT_EMBARQUE), (
            f"Embarque {q.embarque} cai no blackout"
        )


def test_gerar_grade_blackout_retorno_excluded():
    grade = gerar_grade()
    for q in grade:
        assert not _in_blackout(q.retorno, config.BLACKOUT_RETORNO), (
            f"Retorno {q.retorno} cai no blackout"
        )


def test_gerar_grade_retorno_within_janela():
    grade = gerar_grade()
    for q in grade:
        assert q.retorno <= config.JANELA_FIM, (
            f"Retorno {q.retorno} ultrapassa JANELA_FIM"
        )


def test_gerar_grade_min_stay():
    grade = gerar_grade()
    min_noites = config.DIAS_UTEIS[0] + 2
    for q in grade:
        noites = (q.retorno - q.embarque).days
        assert noites >= min_noites, (
            f"Viagem muito curta: {noites} noites (mín {min_noites})"
        )


def test_gerar_grade_max_stay():
    grade = gerar_grade()
    max_noites = config.DIAS_UTEIS[1] + 2
    for q in grade:
        noites = (q.retorno - q.embarque).days
        assert noites <= max_noites, (
            f"Viagem muito longa: {noites} noites (máx {max_noites})"
        )


def test_gerar_grade_destinos_cobertos():
    grade = gerar_grade()
    destinos_grade = {q.destino for q in grade}
    assert destinos_grade == set(config.DESTINOS)


def test_gerar_grade_origens_cobertos():
    grade = gerar_grade()
    origens_grade = {q.origem for q in grade}
    assert origens_grade == set(config.ORIGENS)


def test_gerar_grade_pax():
    grade = gerar_grade()
    assert all(q.pax == config.PAX for q in grade)


def test_gerar_grade_embarque_span():
    grade = gerar_grade()
    embarques = sorted({q.embarque for q in grade})
    # All embarques must be within EMBARQUE_SPAN_DIAS days from JANELA_INI
    # (some may be excluded by blackout, so check max spread)
    for e in embarques:
        diff = (e - config.JANELA_INI).days
        assert 0 <= diff < config.EMBARQUE_SPAN_DIAS
