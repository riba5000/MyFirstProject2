from datetime import date
from decouple import config

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

# Fonte de dados: "travelpayouts" (default) ou "amadeus"
FONTE = config("FONTE", default="travelpayouts")

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
