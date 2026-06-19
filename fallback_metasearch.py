"""
Fallback opcional: cross-check via Playwright + interceptação XHR.

Desligado por padrão (FALLBACK_ENABLED=False em .env).
Use só pontualmente para validar 1–2 combinações que a Amadeus
marcar como boas — não pra varrer a grade toda.

ATENÇÃO: scraping de metabuscadores pode violar Termos de Serviço
e enfrenta anti-bot. Use com critério e sob responsabilidade.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from decouple import config

FALLBACK_ENABLED: bool = config("FALLBACK_ENABLED", cast=bool, default=False)

logger = logging.getLogger(__name__)


def _requires_playwright() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "playwright não instalado. Execute: pip install playwright && playwright install chromium"
        ) from exc


def buscar_google_voos(origem: str, destino: str, embarque: str, retorno: str) -> list[dict[str, Any]]:
    """
    Navega no Google Flights e intercepta a resposta XHR de resultados.
    Retorna lista de dicts brutos extraídos da resposta capturada.

    Params:
        embarque / retorno: ISO date strings (YYYY-MM-DD)
    """
    if not FALLBACK_ENABLED:
        logger.debug("Fallback desabilitado (FALLBACK_ENABLED=False). Retornando [].")
        return []

    _requires_playwright()
    from playwright.sync_api import sync_playwright

    captured: list[dict] = []

    def _handle_response(response):
        url = response.url
        # Google Flights carrega resultados via endpoint interno — adaptar conforme necessário
        if "travel.google.com" in url and "search" in url:
            try:
                body = response.text()
                # A resposta costuma ser JSON prefixado com ")]}'\n" — strip do prefixo
                stripped = body.lstrip(")]}'\n")
                data = json.loads(stripped)
                captured.append(data)
            except Exception as exc:
                logger.debug("Falha ao capturar resposta: %s", exc)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.on("response", _handle_response)

        url = (
            f"https://www.google.com/travel/flights?q="
            f"Flights+from+{origem}+to+{destino}"
            f"+{embarque}+{retorno}"
        )
        logger.info("Fallback: abrindo %s", url)
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3_000)

        browser.close()

    logger.info("Fallback: %d resposta(s) capturada(s)", len(captured))
    return captured
