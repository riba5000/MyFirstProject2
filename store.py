import json
import logging
from pathlib import Path

from models import FareOffer, FareSnapshot

logger = logging.getLogger(__name__)

HISTORY_PATH = Path(__file__).parent / "history.json"


def _load_raw() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read history: %s", exc)
        return []


def append_snapshot(snapshot: FareSnapshot) -> None:
    raw = _load_raw()
    raw.append(json.loads(snapshot.model_dump_json()))
    HISTORY_PATH.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Snapshot appended (%d offers)", len(snapshot.ofertas))


def load_all_offers() -> list[FareOffer]:
    offers: list[FareOffer] = []
    for snap_dict in _load_raw():
        try:
            snap = FareSnapshot.model_validate(snap_dict)
            offers.extend(snap.ofertas)
        except Exception as exc:
            logger.warning("Skipping malformed snapshot: %s", exc)
    return offers
