import logging
import sys
import time
from datetime import datetime, timezone

import config
if config.FONTE == "amadeus":
    from amadeus_client import flight_offers_search
else:
    from travelpayouts_client import flight_offers_search
from dates import gerar_grade
from models import FareSnapshot
from report import enviar_relatorio
from store import append_snapshot, load_all_offers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    rodado_em = datetime.now(timezone.utc)
    logger.info("=== Iniciando rodada %s ===", rodado_em.isoformat())

    grade = gerar_grade()
    logger.info("%d queries geradas", len(grade))

    ofertas = []
    for i, query in enumerate(grade, 1):
        logger.info(
            "[%d/%d] %s→%s %s→%s (%d pax)",
            i, len(grade),
            query.origem, query.destino,
            query.embarque, query.retorno,
            query.pax,
        )
        try:
            resultado = flight_offers_search(query)
            ofertas.extend(resultado)
            logger.debug("  %d oferta(s) recebida(s)", len(resultado))
        except Exception as exc:
            logger.error("  Falha na query: %s", exc)

        time.sleep(config.THROTTLE_SEG)

    if not ofertas:
        logger.warning("Nenhuma oferta encontrada nesta rodada — sem e-mail.")
        return

    snapshot = FareSnapshot(rodado_em=rodado_em, ofertas=ofertas)
    append_snapshot(snapshot)

    if dry_run:
        from pricing import melhor_por_rota
        logger.info("=== DRY-RUN: e-mail NÃO enviado — melhores por rota ===")
        for (orig, dest), o in sorted(melhor_por_rota(ofertas).items()):
            logger.info(
                "  %s→%s  R$ %s/pax  (total R$ %s)  cias=%s  escalas %d+%d  %s→%s",
                orig, dest, o.preco_por_pax, o.preco_total,
                ",".join(o.cias) or "-", o.escalas_ida, o.escalas_volta,
                o.query.embarque, o.query.retorno,
            )
        logger.info("=== Rodada concluída (dry-run): %d ofertas ===", len(ofertas))
        return

    historico = load_all_offers()
    enviar_relatorio(ofertas, historico, rodado_em)
    logger.info("=== Rodada concluída: %d ofertas ===", len(ofertas))


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
