from datetime import date, timedelta
from config import (
    ORIGENS, DESTINOS, PAX,
    JANELA_INI, JANELA_FIM, DIAS_UTEIS,
    EMBARQUE_SPAN_DIAS,
    BLACKOUT_EMBARQUE, BLACKOUT_RETORNO,
)
from models import TripQuery


def _in_blackout(d: date, blackout: tuple[date, date]) -> bool:
    return blackout[0] <= d <= blackout[1]


def selecionar_amostra(grade: list[TripQuery], max_queries: int) -> list[TripQuery]:
    """
    Reduz a grade a no máximo `max_queries`, de forma DETERMINÍSTICA e balanceada.

    Necessário porque o SerpApi tem cota mensal apertada (250 buscas no tier
    gratuito) e a grade cheia tem ~45 queries por rodada.

    Estratégia: divide a cota igualmente entre as rotas (origem, destino) e,
    dentro de cada rota, escolhe pares de datas uniformemente espaçados — assim
    a amostra cobre a janela inteira em vez de só o começo dela.
    """
    if max_queries is None or max_queries <= 0 or len(grade) <= max_queries:
        return list(grade)

    grupos: dict[tuple[str, str], list[TripQuery]] = {}
    for q in grade:
        grupos.setdefault((q.origem, q.destino), []).append(q)

    chaves = list(grupos)
    base, resto = divmod(max_queries, len(chaves))

    escolhidas: list[TripQuery] = []
    sobras: list[TripQuery] = []

    for i, chave in enumerate(chaves):
        itens = grupos[chave]
        cota = base + (1 if i < resto else 0)

        if cota >= len(itens):
            escolhidas.extend(itens)
            continue

        # floor(j * n / cota) é estritamente crescente para cota <= n → índices únicos
        idxs = [(j * len(itens)) // cota for j in range(cota)]
        escolhidas.extend(itens[k] for k in idxs)
        sobras.extend(itens[k] for k in range(len(itens)) if k not in set(idxs))

    # Se alguma rota tinha menos itens que a cota, completa com as sobras
    for q in sobras:
        if len(escolhidas) >= max_queries:
            break
        escolhidas.append(q)

    return sorted(escolhidas, key=lambda q: (q.embarque, q.retorno, q.origem, q.destino))


def gerar_grade() -> list[TripQuery]:
    queries: list[TripQuery] = []
    seen: set[tuple] = set()

    embarques = [JANELA_INI + timedelta(days=i) for i in range(EMBARQUE_SPAN_DIAS)]

    for embarque in embarques:
        if _in_blackout(embarque, BLACKOUT_EMBARQUE):
            continue

        # noites_calendario ≈ dias_uteis + 2 (trânsito ida + volta)
        for n in range(DIAS_UTEIS[0] + 2, DIAS_UTEIS[1] + 3):
            retorno = embarque + timedelta(days=n)

            if retorno > JANELA_FIM:
                continue
            if _in_blackout(retorno, BLACKOUT_RETORNO):
                continue

            for origem in ORIGENS:
                for destino in DESTINOS:
                    key = (origem, destino, embarque, retorno)
                    if key in seen:
                        continue
                    seen.add(key)
                    queries.append(
                        TripQuery(
                            origem=origem,
                            destino=destino,
                            embarque=embarque,
                            retorno=retorno,
                            pax=PAX,
                        )
                    )

    return queries
