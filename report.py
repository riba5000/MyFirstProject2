import io
import logging
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
from models import FareOffer
from pricing import avaliar_alertas, melhor_por_rota

logger = logging.getLogger(__name__)

_DEST_NOME = {"BKK": "Bangkok", "SGN": "Ho Chi Minh", "HAN": "Hanói"}
_ORIG_NOME = {"FLN": "Florianópolis"}


def _fmt_brl(value) -> str:
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_chart(ofertas: list[FareOffer]) -> bytes | None:
    """Return PNG bytes of price-over-time chart, or None if matplotlib unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from collections import defaultdict

        series: dict[str, list] = defaultdict(list)
        for o in sorted(ofertas, key=lambda x: x.coletado_em):
            rota = f"{o.query.origem}→{o.query.destino}"
            series[rota].append((o.coletado_em, float(o.preco_por_pax)))

        fig, ax = plt.subplots(figsize=(10, 5))
        for rota, pts in series.items():
            dates, prices = zip(*pts)
            ax.plot(dates, prices, marker="o", label=rota, linewidth=1.5)

        ax.set_title("Evolução do melhor preço/pax (BRL)")
        ax.set_ylabel("Preço por passageiro (R$)")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except ImportError:
        logger.debug("matplotlib not available; skipping chart")
        return None


def _build_html(
    melhores: dict[tuple[str, str], FareOffer],
    alertas: list[tuple[FareOffer, str]],
    rodado_em: datetime,
    has_chart: bool,
) -> str:
    alerta_rotas = {id(a[0]) for a in alertas}

    linhas = []
    for (orig, dest), o in sorted(melhores.items()):
        destaque = "background:#fff3cd;" if id(o) in alerta_rotas else ""
        linhas.append(
            f"<tr style='{destaque}'>"
            f"<td>{_ORIG_NOME.get(orig, orig)} → {_DEST_NOME.get(dest, dest)}</td>"
            f"<td align='right'><b>{_fmt_brl(o.preco_por_pax)}</b></td>"
            f"<td align='right'>{_fmt_brl(o.preco_total)}</td>"
            f"<td>{', '.join(o.cias)}</td>"
            f"<td align='center'>{o.escalas_ida} + "
            f"{'?' if o.escalas_volta is None else o.escalas_volta}</td>"
            f"<td>{o.query.embarque:%d/%m/%Y} → {o.query.retorno:%d/%m/%Y}</td>"
            f"</tr>"
        )

    alerta_html = ""
    if alertas:
        itens = []
        for oferta, motivo in alertas:
            rota = f"{_ORIG_NOME.get(oferta.query.origem, oferta.query.origem)} → {_DEST_NOME.get(oferta.query.destino, oferta.query.destino)}"
            descricao = (
                f"abaixo do alvo de {_fmt_brl(config.ALVO_HARD_POR_PAX)}/pax"
                if motivo == "hard_target"
                else f"abaixo do P{config.PERCENTIL_ALERTA} histórico"
            )
            itens.append(f"<li><b>{rota}</b>: {_fmt_brl(oferta.preco_por_pax)}/pax — {descricao}</li>")
        alerta_html = (
            "<div style='border:2px solid #e74c3c;padding:12px;margin:16px 0;border-radius:4px'>"
            "<h2 style='color:#e74c3c;margin:0 0 8px'>⚠️ ALERTA DE PREÇO</h2>"
            f"<ul>{''.join(itens)}</ul></div>"
        )

    chart_html = "<p><img src='cid:priceChart' alt='Gráfico de preços' style='max-width:100%'></p>" if has_chart else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'>
<style>
  body{{font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:900px;margin:auto;padding:16px}}
  table{{border-collapse:collapse;width:100%}}
  th,td{{border:1px solid #ddd;padding:8px 10px;text-align:left}}
  th{{background:#2c3e50;color:#fff}}
  tr:nth-child(even){{background:#f9f9f9}}
</style>
</head><body>
<h1>Monitor Tarifas FLN → Sudeste Asiático</h1>
<p>Rodada: {rodado_em:%d/%m/%Y %H:%M UTC} — {config.PAX} passageiros, moeda {config.MOEDA}</p>
{alerta_html}
<h2>Melhores tarifas por rota (esta rodada)</h2>
<table>
<tr>
  <th>Rota</th><th>Preço/pax</th><th>Total ({config.PAX} pax)</th>
  <th>Cias</th><th>Escalas ida+volta</th><th>Datas</th>
</tr>
{''.join(linhas)}
</table>
{chart_html}
<hr><p style='font-size:11px;color:#888'>
Tarifas informativas — confirme valores e disponibilidade antes de comprar.
Fonte: {config.FONTE}. Preços podem não incluir bagagem despachada.
"Escalas ida+volta" com "?" na volta: a busca inicial do Google Flights só
detalha os segmentos da ida.
</p>
</body></html>"""


def enviar_relatorio(
    ofertas_rodada: list[FareOffer],
    historico: list[FareOffer],
    rodado_em: datetime,
) -> None:
    melhores = melhor_por_rota(ofertas_rodada)
    alertas = avaliar_alertas(ofertas_rodada, historico)

    chart_bytes = _build_chart(historico + ofertas_rodada)
    html = _build_html(melhores, alertas, rodado_em, bool(chart_bytes))

    tem_alerta = bool(alertas)
    prefixo = "[ALERTA] " if tem_alerta else ""
    destinos_str = "/".join(d for (_, d) in sorted(melhores))
    assunto = f"{prefixo}Tarifas FLN→{destinos_str} — {rodado_em:%d/%m/%Y}"

    msg = MIMEMultipart("related")
    msg["Subject"] = assunto
    msg["From"] = config.SMTP_FROM
    msg["To"] = config.SMTP_TO

    msg.attach(MIMEText(html, "html", "utf-8"))

    if chart_bytes:
        img = MIMEImage(chart_bytes, _subtype="png")
        img.add_header("Content-ID", "<priceChart>")
        img.add_header("Content-Disposition", "inline", filename="tarifas.png")
        msg.attach(img)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.sendmail(config.SMTP_FROM, [config.SMTP_TO], msg.as_string())

    logger.info("Relatório enviado: '%s'", assunto)
