# Rodando no seu PC (Windows)

Guia passo a passo. São três arquivos, na ordem — basta dar **duplo-clique** em cada um.

---

## Antes de começar: Python

Abra o Prompt de Comando (tecla `Win`, digite `cmd`, Enter) e rode:

```
python --version
```

- Apareceu `Python 3.x.x` → tudo certo, pode seguir.
- Deu erro → baixe em **python.org/downloads** e instale marcando a caixinha
  **"Add Python to PATH"** na primeira tela. Sem essa caixinha marcada, nada funciona.

---

## Passo 1 — `1-instalar.bat`

Duplo-clique. Ele cria um ambiente Python isolado (pasta `.venv`) e instala tudo.
Leva alguns minutos na primeira vez.

No final, ele abre o `.env` no Bloco de Notas para você preencher a senha de e-mail
(veja a seção **Senha de App do Gmail** abaixo). Salve com `Ctrl+S` e feche.

> O ambiente isolado evita que estas bibliotecas conflitem com outros programas
> Python do seu PC.

---

## Passo 2 — `2-testar.bat`

Duplo-clique. Faz **uma coleta e mostra os preços na tela, sem enviar e-mail**.
Serve para conferir que está tudo certo antes de deixar rodando sozinho.

**Confira duas coisas na tela:**

1. **Os preços por pax fazem sentido em reais?**
   Se vierem o dobro ou a metade do esperado, abra o `.env` e troque
   `PRECO_E_TOTAL=true` por `false` (ou vice-versa).

2. **Apareceu algum aviso com a palavra "moeda"?**
   Se sim, os valores podem não ter vindo em reais — me avise, porque aí o alerta
   de R$ 6.500 não seria confiável.

---

## Passo 3 — `3-agendar.bat`

Duplo-clique. Pergunta o horário (padrão 08:00) e registra a tarefa diária no Windows.

A partir daí o monitor roda sozinho, **sem abrir janela**, e envia o e-mail.
Se o PC estiver desligado no horário, a rodada acontece assim que você ligar.

---

## Senha de App do Gmail

O Gmail não aceita sua senha normal em programas. Você precisa de uma "Senha de App":

1. Acesse **myaccount.google.com/security**
2. Ative a **Verificação em duas etapas** (obrigatório para o passo seguinte)
3. Procure por **Senhas de app** e crie uma nova
4. O Google mostra 16 letras — copie
5. No `.env`, cole na linha `SMTP_PASSWORD=` (sem espaços)

---

## Onde ver o que aconteceu

Todo registro fica em **`logs\monitor.log`** — abra com o Bloco de Notas.
É lá que você descobre o que houve na rodada das 8h da manhã.

O histórico de preços coletados fica em `history.json` (é ele que alimenta o
cálculo do P10 e o gráfico do e-mail).

---

## Mudando os parâmetros da busca

Abra `config.py` no Bloco de Notas. As linhas do topo são as que importam:

| Linha | O que faz |
|---|---|
| `DESTINOS` | Aeroportos monitorados (`BKK`, `SGN`, `HAN`) |
| `JANELA_INI` / `JANELA_FIM` | Período da viagem |
| `DIAS_UTEIS` | Duração da estadia (15 a 20 dias) |
| `ALVO_HARD_POR_PAX` | Preço que dispara o alerta (R$ 6.500 por pessoa) |
| `BLACKOUT_EMBARQUE` | Datas a evitar no embarque (pico de fim de ano) |

Depois de mudar, rode `2-testar.bat` para conferir.

---

## Comandos úteis

Abra o Prompt de Comando **na pasta do projeto** e use:

| Para | Comando |
|---|---|
| Rodar agora e enviar e-mail | `.venv\Scripts\python.exe main.py` |
| Rodar sem enviar e-mail | `.venv\Scripts\python.exe main.py --dry-run` |
| Disparar a tarefa agendada | `powershell Start-ScheduledTask -TaskName MonitorTarifasAsia` |
| Cancelar o agendamento | `powershell -ExecutionPolicy Bypass -File agendar.ps1 -Remover` |
| Rodar os testes | `.venv\Scripts\python.exe -m pytest tests\ -q` |

---

## Se der problema

| Sintoma | Causa provável |
|---|---|
| `python nao encontrado` | Python sem "Add to PATH" — reinstale marcando a caixinha |
| Todas as buscas voltam vazias | Sem internet, ou o Google mudou o formato interno (a lib precisa de atualização) |
| Aviso de "moeda" no log | O pedido de preços em reais não pegou — me avise |
| E-mail não chega | `SMTP_PASSWORD` não é uma Senha de App, ou faltou a verificação em duas etapas |
| Preços com o dobro/metade do valor | Inverta `PRECO_E_TOTAL` no `.env` |

---

## Duas ressalvas honestas

- **O PC precisa estar ligado** em algum momento do dia para a rodada acontecer.
  Não há nada rodando na nuvem — se o computador ficar dias desligado, não há coleta
  e o histórico fica com buracos.
- **A fonte de dados é frágil por natureza.** A biblioteca conversa com o formato
  interno do Google Flights, que muda sem aviso. Quando quebrar, o sintoma é
  "todas as buscas voltam vazias" — a correção costuma ser
  `.venv\Scripts\python.exe -m pip install --upgrade google-flights-search`.
