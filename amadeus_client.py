import time
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx

import config
from models import FareOffer, TripQuery

logger = logging.getLogger(__name__)

_token: str = ""
_token_expires_at: float = 0.0
_TOKEN_MARGIN_SEC = 60


def _get_token() -> str:
    global _token, _token_expires_at

    if _token and time.monotonic() < _token_expires_at:
        return _token

    resp = httpx.post(
        f"{config.AMADEUS_BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": config.AMADEUS_CLIENT_ID,
            "client_secret": config.AMADEUS_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()

    _token = body["access_token"]
    _token_expires_at = time.monotonic() + body["expires_in"] - _TOKEN_MARGIN_SEC
    logger.debug("Amadeus token refreshed, expires in %ds", body["expires_in"])
    return _token


def _iso_duration_to_minutes(iso: str) -> int:
    """Convert ISO 8601 duration (PT14H30M) to total minutes."""
    import re
    h = int(m := re.search(r"(\d+)H", iso)) and int(m.group(1)) if re.search(r"(\d+)H", iso) else 0
    mins = int(re.search(r"(\d+)M", iso).group(1)) if re.search(r"(\d+)M", iso) else 0
    return h * 60 + mins


def _parse_offers(data: list[dict], query: TripQuery) -> list[FareOffer]:
    now = datetime.now(timezone.utc)
    offers: list[FareOffer] = []

    for item in data:
        price = Decimal(item["price"]["grandTotal"])
        price_pax = (price / query.pax).quantize(Decimal("0.01"))

        cias = item.get("validatingAirlineCodes", [])

        itineraries = item.get("itineraries", [])
        if len(itineraries) < 2:
            continue

        def _escalas(it: dict) -> int:
            return max(0, len(it.get("segments", [])) - 1)

        def _dur(it: dict) -> int:
            return _iso_duration_to_minutes(it.get("duration", "PT0M"))

        offers.append(
            FareOffer(
                query=query,
                preco_total=price,
                preco_por_pax=price_pax,
                cias=cias,
                escalas_ida=_escalas(itineraries[0]),
                escalas_volta=_escalas(itineraries[1]),
                duracao_ida_min=_dur(itineraries[0]),
                duracao_volta_min=_dur(itineraries[1]),
                coletado_em=now,
            )
        )

    return offers


def flight_offers_search(query: TripQuery) -> list[FareOffer]:
    token = _get_token()

    params: dict = {
        "originLocationCode": query.origem,
        "destinationLocationCode": query.destino,
        "departureDate": query.embarque.isoformat(),
        "returnDate": query.retorno.isoformat(),
        "adults": str(query.pax),
        "currencyCode": config.MOEDA,
        "max": str(config.MAX_OFERTAS_POR_QUERY),
    }
    if config.NONSTOP_ONLY:
        params["nonStop"] = "true"

    resp = httpx.get(
        f"{config.AMADEUS_BASE_URL}/v2/shopping/flight-offers",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )

    if resp.status_code == 429:
        logger.warning("Rate-limited by Amadeus; sleeping 5s")
        time.sleep(5)
        return flight_offers_search(query)

    resp.raise_for_status()
    data = resp.json().get("data", [])
    return _parse_offers(data, query)
