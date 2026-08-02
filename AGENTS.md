# agente-tarifas-asia

Monitor de tarifa paga FLN → Sudeste Asiático via Amadeus Self-Service API.

## STATUS (2026-08-02): fonte = gf_search (Google Flights, sem cota). Falta 1 teste real.

### Histórico das fontes (não repetir os becos sem saída)

- **Amadeus Self-Service** — ☠️ **DESATIVADA em 17/07/2026**: a Amadeus fechou novos
  cadastros e desligou as chaves existentes, empurrando todos para o Enterprise
  (exige acreditação IATA/ARC). `amadeus_client.py` fica só como histórico.
- **Travelpayouts/Aviasales (grátis)** — ❌ **não serve**: o cache cobre só as buscas
  das últimas 48h dos usuários do Aviasales, então datas futuras voltam sempre vazias.
  Confirmado em teste real + doc. O real-time deles exige 50k usuários ativos/mês.
- **SerpApi / google_flights** — 🟡 implementado e funcional, mas **250 buscas/mês**
  obrigam a amostrar ~13% da grade. Fica como plano B (`FONTE=serpapi` +
  `MAX_QUERIES_POR_RODADA=6`).
- **Playwright na UI do Google** (`fallback_metasearch.py`) — ❌ inviável em 2026:
  exige stealth + proxy residencial + serviço de CAPTCHA. Mantido desligado.
- **gf_search** (pacote `google-flights-search`) — ✅ **em uso**: SSR do Google
  Flights, sem chave e **sem cota** → roda a grade inteira (45/dia). Escolhida por
  tratar aeroportos regionais, caso do FLN (a `fast-flights` retorna vazio neles).

### Armadilhas do gf_search (tratadas em gf_search_client.py — não "simplificar")

1. **Moeda**: a lib fixa `hl=zh-TW` e monta o preço como `f"TWD {valor}"` — o prefixo
   é colado, não indica a moeda real. Por isso o rótulo é ignorado e
   `_forcar_locale_br()` injeta `curr/gl/hl` via patch em `httpx.Client.get`.
   Rede de segurança: `_faixa_plausivel_brl()` alerta se a ordem de grandeza
   sugerir que a conversão não pegou.
2. **Falha silenciosa**: retorna `[]` tanto para "rota sem voos" quanto para erro de
   rede. O log diz explicitamente que as duas causas são possíveis.
3. **Volta**: não há separação confiável entre segmentos de ida e volta, então
   `escalas_volta`/`duracao_volta_min` são `None` — nunca zero, que seria mentira.

### Pendência para retomar

Rodar `python main.py --dry-run` uma vez e conferir dois pontos no log:
- os preços por pax fazem sentido em R$? Se vierem dobrados/pela metade, inverter
  `PRECO_E_TOTAL` no `.env`;
- apareceu aviso de "moeda"? Então a injeção de locale não pegou (ver armadilha 1).

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
