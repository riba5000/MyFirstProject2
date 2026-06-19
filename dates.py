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
