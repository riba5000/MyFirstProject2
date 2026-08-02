from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class TripQuery(BaseModel):
    origem: str
    destino: str
    embarque: date
    retorno: date
    pax: int


class FareOffer(BaseModel):
    query: TripQuery
    preco_total: Decimal
    preco_por_pax: Decimal
    cias: list[str]
    escalas_ida: int
    # None = não disponível nesta fonte. O Google Flights (SerpApi) só devolve os
    # detalhes da volta numa 2ª chamada (departure_token), que gastaria o dobro da cota.
    escalas_volta: int | None = None
    duracao_ida_min: int
    duracao_volta_min: int | None = None
    coletado_em: datetime


class FareSnapshot(BaseModel):
    rodado_em: datetime
    ofertas: list[FareOffer]
