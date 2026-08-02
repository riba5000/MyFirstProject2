import logging
import sys
import time
from datetime import datetime, timezone

import config
import quota
if config.FONTE == "amadeus":
    from amadeus_client import flight_offers_search
elif config.FONTE == "travelpayouts":
    from travelpayouts_client import flight_offers_search
else:
    from serpapi_client import flight_offers_search
from dates import gerar_grade, selecionar_amostra
from models import FareSnapshot
from report import enviar_relatorio
from store import append_snapshot, load_all_offers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    rodado_em = datetime.now(timezone.utc)
    logger.info("=== Iniciando rodada %s ===", rodado_em.isoformat())

    grade_cheia = gerar_grade()
    grade = selecionar_amostra(grade_cheia, config.MAX_QUERIES_POR_RODADA)
    logger.info("%d queries geradas → %d selecionadas (teto por rodada)",
                len(grade_cheia), len(grade))

    usa_cota = config.FONTE == "serpapi"
    if usa_cota:
        usado = quota.uso_do_mes(rodado_em)
        limite = config.SERPAPI_QUOTA_MENSAL
        if not quota.pode_consultar(usado, len(grade), limite):
            logger.error(
                "Cota mensal do SerpApi esgotada: %d/%d usadas, %d necessárias. "
                "Rodada cancelada para não gerar cobrança.",
                usado, limite, len(grade),
            )
            return
        logger.info("Cota SerpApi: %d/%d usadas neste mês; esta rodada usa %d",
                    usado, limite, len(grade))

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
            if usa_cota:
                quota.registrar_uso(rodado_em)   # conta antes: erro de rede pode ter consumido
            resultado = flight_offers_search(query)
            ofertas.extend(resultado)
            logger.info("  %d oferta(s) recebida(s)", len(resultado))
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
            volta = "?" if o.escalas_volta is None else str(o.escalas_volta)
            logger.info(
                "  %s→%s  R$ %s/pax  (total R$ %s)  cias=%s  escalas %d+%s  %s→%s",
                orig, dest, o.preco_por_pax, o.preco_total,
                ",".join(o.cias) or "-", o.escalas_ida, volta,
                o.query.embarque, o.query.retorno,
            )
        logger.info("=== Rodada concluída (dry-run): %d ofertas ===", len(ofertas))
        return

    historico = load_all_offers()
    enviar_relatorio(ofertas, historico, rodado_em)
    logger.info("=== Rodada concluída: %d ofertas ===", len(ofertas))


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
