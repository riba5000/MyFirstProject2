from datetime import date
from decouple import config

# O SerpApi lê o Google Flights (inventário real), então FLN funciona direto —
# não é preciso o paliativo de monitorar GRU que a fonte de cache exigia.
ORIGENS   = ["FLN"]
DESTINOS  = ["BKK", "SGN", "HAN"]
PAX       = 2
MOEDA     = "BRL"

JANELA_INI  = date(2026, 12, 12)
JANELA_FIM  = date(2027, 1, 30)
DIAS_UTEIS  = (15, 20)

EMBARQUE_SPAN_DIAS = 7

BLACKOUT_EMBARQUE = (date(2026, 12, 20), date(2027, 1, 2))
BLACKOUT_RETORNO  = (date(2026, 12, 24), date(2027, 1, 4))

ALVO_HARD_POR_PAX = 6500.00
PERCENTIL_ALERTA  = 10

NONSTOP_ONLY          = False
MAX_OFERTAS_POR_QUERY = 5
THROTTLE_SEG          = 0.5

# Fonte de dados: "serpapi" (default) | "travelpayouts" | "amadeus"
#   serpapi       → Google Flights, inventário real, cota 250/mês no gratuito
#   travelpayouts → cache de 48h; NÃO serve para datas futuras (ver AGENTS.md)
#   amadeus       → desativada pela Amadeus em 17/07/2026; mantido só como histórico
FONTE = config("FONTE", default="serpapi")

SERPAPI_KEY = config("SERPAPI_KEY", default="")
# True  → `price` do Google Flights é o total do grupo (padrão)
# False → `price` é por passageiro
SERPAPI_PRECO_E_TOTAL = config("SERPAPI_PRECO_E_TOTAL", cast=bool, default=True)
# Cota do tier gratuito. A trava é local e conservadora (ver quota.py).
SERPAPI_QUOTA_MENSAL = config("SERPAPI_QUOTA_MENSAL", cast=int, default=250)

# Teto de buscas por rodada. 6/rodada × 1 rodada/dia ≈ 180/mês, com folga
# dentro dos 250 gratuitos. A grade cheia (~45) é amostrada até este teto.
MAX_QUERIES_POR_RODADA = config("MAX_QUERIES_POR_RODADA", cast=int, default=6)

TRAVELPAYOUTS_TOKEN    = config("TRAVELPAYOUTS_TOKEN",    default="")
TRAVELPAYOUTS_BASE_URL = config("TRAVELPAYOUTS_BASE_URL", default="https://api.travelpayouts.com")

AMADEUS_CLIENT_ID     = config("AMADEUS_CLIENT_ID",     default="")
AMADEUS_CLIENT_SECRET = config("AMADEUS_CLIENT_SECRET", default="")
AMADEUS_BASE_URL      = config("AMADEUS_BASE_URL",      default="https://test.api.amadeus.com")

SMTP_HOST     = config("SMTP_HOST",     default="smtp.gmail.com")
SMTP_PORT     = config("SMTP_PORT",     cast=int, default=587)
SMTP_USER     = config("SMTP_USER",     default="")
SMTP_PASSWORD = config("SMTP_PASSWORD", default="")
SMTP_FROM     = config("SMTP_FROM",     default="")
SMTP_TO       = config("SMTP_TO",       default="")
