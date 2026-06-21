"""
Diagnóstico da Travelpayouts Data API. Roda algumas variações e mostra a
resposta crua, para entender por que o cache volta vazio.

Uso:  python diag.py
"""
import json
import httpx
import config

URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def call(label: str, **params) -> None:
    params.setdefault("currency", "brl")
    params["token"] = config.TRAVELPAYOUTS_TOKEN
    print(f"\n=== {label} ===")
    try:
        r = httpx.get(URL, params=params, timeout=20)
    except Exception as exc:
        print("ERRO de conexão:", exc)
        return
    print("Status:", r.status_code)
    try:
        body = r.json()
    except Exception:
        print("Body (texto):", r.text[:300])
        return
    data = body.get("data", [])
    print("success:", body.get("success"), "| nº de itens:", len(data))
    if body.get("error"):
        print("error:", body["error"])
    if data:
        print("1º item:", json.dumps(data[0], ensure_ascii=False))


# 1. Nosso caso real: dez/2026 (mês inteiro), GRU->BKK
call("GRU->BKK dez/2026 (mês)", origin="GRU", destination="BKK", departure_at="2026-12")

# 2. Controle perto: próximos meses (cache deve existir), GRU->BKK
call("GRU->BKK ago/2026 (mês)", origin="GRU", destination="BKK", departure_at="2026-08")

# 3. Controle amplo: só ida, sem data específica
call("GRU->BKK só ida (sem data)", origin="GRU", destination="BKK", one_way="true")

# 4. Rota mega popular como sanity check
call("GRU->MIA só ida (sem data)", origin="GRU", destination="MIA", one_way="true")

# 5. Endpoint alternativo mais permissivo: cheapest do mês (v1)
print("\n=== [v1] prices/cheap GRU->BKK dez/2026 ===")
try:
    r = httpx.get(
        "https://api.travelpayouts.com/v1/prices/cheap",
        params={"origin": "GRU", "destination": "BKK", "depart_date": "2026-12",
                "currency": "brl", "token": config.TRAVELPAYOUTS_TOKEN},
        timeout=20,
    )
    print("Status:", r.status_code, "| Body:", r.text[:400])
except Exception as exc:
    print("ERRO:", exc)
