from decimal import Decimal
from statistics import quantiles

import config
from models import FareOffer


def _percentil(values: list[Decimal], p: int) -> Decimal:
    """Return the p-th percentile of a list of Decimal values."""
    if not values:
        raise ValueError("empty values list")
    sorted_vals = sorted(float(v) for v in values)
    # quantiles returns (n-1) cut points; map p/100 via interpolation
    if len(sorted_vals) == 1:
        return Decimal(str(sorted_vals[0]))
    cuts = quantiles(sorted_vals, n=100)
    idx = max(0, p - 1)
    return Decimal(str(cuts[min(idx, len(cuts) - 1)]))


def melhor_por_rota(
    ofertas: list[FareOffer],
) -> dict[tuple[str, str], FareOffer]:
    """Return the cheapest FareOffer per (origem, destino) route."""
    melhor: dict[tuple[str, str], FareOffer] = {}
    for o in ofertas:
        key = (o.query.origem, o.query.destino)
        if key not in melhor or o.preco_por_pax < melhor[key].preco_por_pax:
            melhor[key] = o
    return melhor


def avaliar_alertas(
    ofertas_rodada: list[FareOffer],
    historico: list[FareOffer],
) -> list[tuple[FareOffer, str]]:
    """
    Return list of (offer, reason) for offers that trigger an alert.
    Reasons: 'hard_target' | 'p10_historico'
    """
    alertas: list[tuple[FareOffer, str]] = []
    melhores = melhor_por_rota(ofertas_rodada)

    for rota, melhor in melhores.items():
        if melhor.preco_por_pax <= Decimal(str(config.ALVO_HARD_POR_PAX)):
            alertas.append((melhor, "hard_target"))
            continue

        hist_rota = [
            o.preco_por_pax
            for o in historico
            if (o.query.origem, o.query.destino) == rota
        ]
        if len(hist_rota) >= 10:
            p10 = _percentil(hist_rota, config.PERCENTIL_ALERTA)
            if melhor.preco_por_pax < p10:
                alertas.append((melhor, "p10_historico"))

    return alertas
