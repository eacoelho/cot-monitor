# cot_analyst.py — Generates market insights via Groq (Llama 3.3)

import logging
import time

import pandas as pd
from groq import Groq

from config import COMMODITIES, GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct_change(series: pd.Series) -> float:
    """Percentage change from first to last non-null value."""
    clean = series.dropna()
    if len(clean) < 2:
        return 0.0
    return ((clean.iloc[-1] - clean.iloc[0]) / abs(clean.iloc[0])) * 100


def _direction(value: float) -> str:
    if value > 5:
        return "alta"
    if value < -5:
        return "queda"
    return "estável"


def _build_commodity_summary(name: str, cot_df: pd.DataFrame, price_df: pd.DataFrame) -> str:
    """
    Build a structured text block describing a single commodity's recent COT
    and price dynamics, to be fed to the LLM.
    """
    net = cot_df["net_position"]
    latest_net   = net.iloc[-1]
    prior_net    = net.iloc[-2] if len(net) >= 2 else latest_net
    net_4w_ago   = net.iloc[-4] if len(net) >= 4 else net.iloc[0]
    net_12m_ago  = net.iloc[0]
    net_change_wk  = latest_net - prior_net
    net_change_4w  = latest_net - net_4w_ago
    net_change_12m = latest_net - net_12m_ago
    net_max   = net.max()
    net_min   = net.min()
    net_pct_max = ((latest_net - net_min) / (net_max - net_min) * 100) if (net_max != net_min) else 50

    price = price_df["close"]
    latest_price  = price.iloc[-1]
    price_4w_ago  = price.iloc[-4] if len(price) >= 4 else price.iloc[0]
    price_12m_ago = price.iloc[0]
    price_chg_4w  = _pct_change(price.iloc[-4:])
    price_chg_12m = _pct_change(price)

    sign = lambda x: f"+{x:,.0f}" if x >= 0 else f"{x:,.0f}"

    return (
        f"Commodity: {name}\n"
        f"  Posição Net Fundos (última semana): {sign(latest_net)} contratos\n"
        f"  Variação semana anterior: {sign(net_change_wk)} contratos\n"
        f"  Variação 4 semanas: {sign(net_change_4w)} contratos\n"
        f"  Variação 12 meses: {sign(net_change_12m)} contratos\n"
        f"  Percentil histórico 12m da posição net: {net_pct_max:.0f}%\n"
        f"  (máximo 12m: {sign(net_max)}, mínimo 12m: {sign(net_min)})\n"
        f"  Preço atual: {latest_price:,.2f}\n"
        f"  Variação preço 4 semanas: {price_chg_4w:+.1f}%\n"
        f"  Variação preço 12 meses: {price_chg_12m:+.1f}%\n"
    )


def _call_groq(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    logger.error("Groq failed after all retries.")
    return "⚠️ Análise indisponível no momento."


# ── Main function ─────────────────────────────────────────────────────────────

def generate_analysis(data: dict[str, dict]) -> str:
    """
    Generates a full Telegram-ready text with one paragraph per commodity.

    Parameters
    ----------
    data : output of cot_collector.collect_all()

    Returns
    -------
    str : formatted analysis text in Brazilian Portuguese
    """
    logger.info("Building commodity summaries for LLM prompt...")

    summaries = []
    for commodity in COMMODITIES:
        name = commodity["display_name"]
        if name not in data:
            continue
        summary = _build_commodity_summary(
            name,
            data[name]["cot"],
            data[name]["price"],
        )
        summaries.append(summary)

    data_block = "\n".join(summaries)

    prompt = f"""Você é um analista sênior de mercados agrícolas. Com base nos dados abaixo do relatório COT (Commitment of Traders) da CFTC, referentes à posição de fundos gestores (Managed Money) em futuros e opções, gere um resumo em português brasileiro para envio via Telegram.

INSTRUÇÕES:
- Para cada commodity, escreva um parágrafo curto (3 a 5 linhas).
- Identifique se os fundos estão comprados ou vendidos, em qual direção a posição se moveu nas últimas semanas, e se o posicionamento está em nível extremo (percentil alto ou baixo).
- Relacione o movimento da posição com o comportamento do preço: convergência ou divergência.
- Use linguagem objetiva e profissional, sem floreios.
- Não repita os números brutos: interprete-os.
- Separe cada commodity com uma linha em branco.
- Use emojis de forma sóbria: 🟢 para posição/tendência positiva, 🔴 para negativa, 🟡 para neutra/mista.
- Inicie cada commodity com seu nome em negrito no formato Telegram: *Nome da Commodity*

DADOS:
{data_block}

Gere o relatório agora:"""

    logger.info("Calling Groq for analysis...")
    result = _call_groq(prompt)
    logger.info("Analysis generated successfully.")
    return result
