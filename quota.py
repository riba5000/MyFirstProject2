"""
Controle local da cota mensal do SerpApi (tier gratuito: 250 buscas/mês).

O contador é local e conservador: conta toda busca DISPARADA, mesmo que ela
volte vazia. O SerpApi não cobra buscas com erro, então o número real gasto
tende a ser menor que o daqui — é de propósito, para nunca estourar.

`_chave_mes` e `pode_consultar` são puros (testáveis sem relógio nem disco).
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

QUOTA_PATH = Path(__file__).parent / "serpapi_quota.json"


def _chave_mes(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def pode_consultar(usado: int, a_consultar: int, limite: int) -> bool:
    """Puro: cabe mais `a_consultar` buscas sem passar de `limite`?"""
    return usado + a_consultar <= limite


def _ler() -> dict:
    if not QUOTA_PATH.exists():
        return {}
    try:
        return json.loads(QUOTA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Não consegui ler o arquivo de cota: %s", exc)
        return {}


def uso_do_mes(agora: datetime) -> int:
    return int(_ler().get(_chave_mes(agora), 0))


def registrar_uso(agora: datetime, n: int = 1) -> int:
    """Soma `n` ao contador do mês corrente e devolve o total do mês."""
    dados = _ler()
    chave = _chave_mes(agora)
    dados[chave] = int(dados.get(chave, 0)) + n
    try:
        QUOTA_PATH.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Não consegui gravar o arquivo de cota: %s", exc)
    return dados[chave]
