# agente-tarifas-asia

Monitor de tarifa paga FLN → Sudeste Asiático via Amadeus Self-Service API.

## STATUS (2026-08-02): fonte = SerpApi (Google Flights). Falta 1 teste real.

### Histórico das fontes (não repetir os becos sem saída)

- **Amadeus Self-Service** — ☠️ **DESATIVADA em 17/07/2026**: a Amadeus fechou novos
  cadastros e desligou as chaves existentes, empurrando todos para o Enterprise
  (exige acreditação IATA/ARC). `amadeus_client.py` fica só como histórico.
- **Travelpayouts/Aviasales (grátis)** — ❌ **não serve**: o cache cobre só as buscas
  das últimas 48h dos usuários do Aviasales, então datas futuras voltam sempre vazias.
  Confirmado em teste real + doc. Não é bug, é limitação do produto. O real-time deles
  exige 50k usuários ativos/mês.
- **SerpApi / google_flights** — ✅ **em uso**: resultado real do Google Flights,
  inclusive datas distantes. Restrição: **250 buscas/mês** no tier gratuito.

### Consequências de projeto da cota

- `dates.selecionar_amostra()` corta a grade cheia (45) para `MAX_QUERIES_POR_RODADA` (6),
  de forma determinística e balanceada entre destinos, cobrindo a janela inteira.
- `quota.py` mantém um contador local por mês e **cancela a rodada** antes de estourar.
  Conta toda busca disparada (conservador — o SerpApi não cobra erro).
- `scheduler.py` roda **1×/dia** (2×/dia estouraria): 6 × 30 = 180/mês, folga de 70.

### Pendência para retomar

Rodar `python main.py --dry-run` uma vez e conferir a linha
"Interpretação de preço: ..." no log. Se o valor por pax vier o dobro/metade do
esperado, inverter `SERPAPI_PRECO_E_TOTAL` no `.env` (só isso, sem mexer no código).

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
