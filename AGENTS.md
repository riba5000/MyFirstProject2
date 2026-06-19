# agente-tarifas-asia

Monitor de tarifa paga FLN → Sudeste Asiático via Amadeus Self-Service API.

## Arquitetura

- **Core puro/testável**: `dates.py`, `pricing.py` — não chamam rede; cobertos por `tests/`.
- **Bordas com I/O**: `amadeus_client.py`, `store.py`, `report.py`, `scheduler.py`.
- **Segredos**: apenas em `.env` (`AMADEUS_*`, `SMTP_*`) — nunca commitar.

## Padrões do projeto

- Pydantic para todos os modelos de dados (`models.py`).
- Token OAuth2 cacheado em memória até `expires_in - 60s` (`amadeus_client.py`).
- Persistência JSON append-only (`history.json` via `store.py`).
- `THROTTLE_SEG` entre queries para respeitar rate limit da Amadeus.

## Tarefa típica

Implementar/ajustar um módulo por vez, rodar `tests/` antes de integrar:

```bash
python -m pytest tests/ -v
```

## Ordem de ambiente

1. Copiar `.env.example` para `.env` e preencher credenciais.
2. Usar `AMADEUS_BASE_URL=https://test.api.amadeus.com` para desenvolvimento.
3. Migrar para `https://api.amadeus.com` (produção) quando os números fizerem sentido.
4. Fallback Playwright (`fallback_metasearch.py`) desligado por padrão — ativar via `FALLBACK_ENABLED=true` só para cross-check pontual.

## Pontos de atenção

- FLN não tem voo direto para a Ásia — itinerários sempre multi-segmento.
- `grandTotal` Amadeus = tarifa-base + taxas; bagagem despachada confirma-se no checkout.
- Cota gratuita Amadeus tem limite mensal — reduzir `EMBARQUE_SPAN_DIAS` ou `DESTINOS` se necessário.
- Alerta P10 exige `>= 10` pontos históricos para evitar falso positivo.
