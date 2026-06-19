import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from main import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Roda às 08:00 e 20:00 (horário de Brasília = UTC-3)
_BRT_TO_UTC_OFFSET = 3

scheduler = BlockingScheduler(timezone="UTC")
scheduler.add_job(
    run,
    CronTrigger(hour=8 + _BRT_TO_UTC_OFFSET, minute=0),
    id="rodada_manha",
    name="Rodada manhã (08:00 BRT)",
    misfire_grace_time=300,
)
scheduler.add_job(
    run,
    CronTrigger(hour=20 + _BRT_TO_UTC_OFFSET, minute=0),
    id="rodada_noite",
    name="Rodada noite (20:00 BRT)",
    misfire_grace_time=300,
)

if __name__ == "__main__":
    logger.info("Scheduler iniciado — rodadas às 08:00 e 20:00 BRT")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado.")
