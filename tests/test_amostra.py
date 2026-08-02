"""Tests for dates.selecionar_amostra — pure, no network.

A amostragem existe por causa da cota do SerpApi: precisa ser determinística,
respeitar o teto e cobrir a janela inteira (não só o começo dela).
"""
from datetime import date, timedelta

from dates import gerar_grade, selecionar_amostra
from models import TripQuery


def _grade_sintetica(destinos=("BKK", "SGN", "HAN"), n_por_destino=15) -> list[TripQuery]:
    base = date(2026, 12, 14)
    out = []
    for d in destinos:
        for i in range(n_por_destino):
            emb = base + timedelta(days=i)
            out.append(TripQuery(origem="FLN", destino=d, embarque=emb,
                                 retorno=emb + timedelta(days=20), pax=2))
    return out


def test_respeita_o_teto():
    assert len(selecionar_amostra(_grade_sintetica(), 6)) == 6


def test_nao_corta_quando_grade_ja_cabe():
    grade = _grade_sintetica(n_por_destino=1)   # 3 itens
    assert len(selecionar_amostra(grade, 10)) == 3


def test_deterministica():
    grade = _grade_sintetica()
    a = selecionar_amostra(grade, 6)
    b = selecionar_amostra(grade, 6)
    assert [(q.destino, q.embarque) for q in a] == [(q.destino, q.embarque) for q in b]


def test_equilibra_entre_destinos():
    amostra = selecionar_amostra(_grade_sintetica(), 6)
    por_destino = {}
    for q in amostra:
        por_destino[q.destino] = por_destino.get(q.destino, 0) + 1
    assert por_destino == {"BKK": 2, "SGN": 2, "HAN": 2}


def test_cobre_a_janela_nao_so_o_inicio():
    """Com 2 por destino, deve pegar uma data do começo e outra bem depois."""
    amostra = selecionar_amostra(_grade_sintetica(n_por_destino=15), 6)
    bkk = sorted(q.embarque for q in amostra if q.destino == "BKK")
    assert (bkk[-1] - bkk[0]).days >= 5, "amostra concentrada no início da janela"


def test_sem_duplicatas():
    amostra = selecionar_amostra(_grade_sintetica(), 9)
    chaves = [(q.origem, q.destino, q.embarque, q.retorno) for q in amostra]
    assert len(chaves) == len(set(chaves))


def test_itens_vem_da_grade_original():
    grade = _grade_sintetica()
    originais = {(q.origem, q.destino, q.embarque, q.retorno) for q in grade}
    for q in selecionar_amostra(grade, 6):
        assert (q.origem, q.destino, q.embarque, q.retorno) in originais


def test_teto_zero_ou_negativo_nao_filtra():
    grade = _grade_sintetica(n_por_destino=2)
    assert len(selecionar_amostra(grade, 0)) == len(grade)


def test_teto_menor_que_numero_de_rotas():
    """Teto 2 com 3 destinos: não pode estourar nem quebrar."""
    assert len(selecionar_amostra(_grade_sintetica(), 2)) <= 2


def test_grade_real_cabe_no_teto_configurado():
    """Com teto > 0 a grade real é cortada; com 0 (sem cota) roda inteira."""
    import config
    grade = gerar_grade()
    amostra = selecionar_amostra(grade, config.MAX_QUERIES_POR_RODADA)
    if config.MAX_QUERIES_POR_RODADA > 0:
        assert len(amostra) <= config.MAX_QUERIES_POR_RODADA
    else:
        assert len(amostra) == len(grade)
