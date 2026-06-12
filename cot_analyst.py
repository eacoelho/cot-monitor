# cot_analyst.py — Generates one analysis paragraph per commodity via Groq

import logging
import time

import pandas as pd
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

_groq_client: Groq | None = None


def _get_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


# ── Number formatting helpers ─────────────────────────────────────────────────

def _br(value: float, decimals: int = 0) -> str:
    """Absolute value with Brazilian separators: 45.200  or  1.042,50"""
    s = f"{abs(value):,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _signed_br(value: float, decimals: int = 0) -> str:
    """Signed value with Brazilian separators: +45.200  or  -1,8"""
    sign = "+" if value >= 0 else "-"
    return f"{sign}{_br(abs(value), decimals)}"


# ── Header block (deterministic, shown before the AI analysis) ────────────────

def _build_header(name: str, cot_df: pd.DataFrame, price_df: pd.DataFrame) -> str:
    """
    Returns a 3-line summary block:
        *Soja*
        📊 Net Fundos: +45.200 contratos  (+3.100 na semana)
        💰 Preço: 1.042,50  (-1,8% na semana)
    """
    net   = cot_df["net_position"]
    price = price_df["close"]

    latest_net = net.iloc[-1]
    net_change = (latest_net - net.iloc[-2]) if len(net) >= 2 else 0.0

    latest_price = price.iloc[-1]
    prior_price  = price.iloc[-2] if len(price) >= 2 else latest_price
    price_pct    = ((latest_price - prior_price) / abs(prior_price) * 100) if prior_price != 0 else 0.0

    return (
        f"*{name}*\n"
        f"📊 Net Fundos: {_signed_br(latest_net)} contratos  ({_signed_br(net_change)} na semana)\n"
        f"💰 Preço: {_br(latest_price, 2)}  ({_signed_br(price_pct, 1)}% na semana)"
    )


# ── Data block for the AI prompt ──────────────────────────────────────────────

def _pct_change(series: pd.Series) -> float:
    clean = series.dropna()
    if len(clean) < 2:
        return 0.0
    base = clean.iloc[0]
    if base == 0:
        return 0.0
    return ((clean.iloc[-1] - base) / abs(base)) * 100


def _build_data_block(name: str, cot_df: pd.DataFrame, price_df: pd.DataFrame) -> str:
    net   = cot_df["net_position"]
    price = price_df["close"]

    latest_net    = net.iloc[-1]
    prior_net     = net.iloc[-2] if len(net) >= 2 else latest_net
    net_4w_ago    = net.iloc[-4] if len(net) >= 4 else net.iloc[0]
    net_change_wk = latest_net - prior_net
    net_change_4w = latest_net - net_4w_ago
    net_max       = net.max()
    net_min       = net.min()
    net_pct       = ((latest_net - net_min) / (net_max - net_min) * 100) if (net_max != net_min) else 50

    latest_price  = price.iloc[-1]
    price_chg_4w  = _pct_change(price.iloc[-4:])
    price_chg_12m = _pct_change(price)

    s = lambda x: f"+{x:,.0f}" if x >= 0 else f"{x:,.0f}"

    return (
        f"Commodity: {name}\n"
        f"  Posição Net atual: {s(latest_net)} contratos\n"
        f"  Variação na semana: {s(net_change_wk)} contratos\n"
        f"  Variação em 4 semanas: {s(net_change_4w)} contratos\n"
        f"  Percentil histórico 12m: {net_pct:.0f}% (máx {s(net_max)}, mín {s(net_min)})\n"
        f"  Preço atual: {latest_price:,.2f}\n"
        f"  Variação preço 4 semanas: {price_chg_4w:+.1f}%\n"
        f"  Variação preço 12 meses: {price_chg_12m:+.1f}%\n"
    )


def _call_groq(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = _get_client().chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    logger.error("Groq failed after all retries.")
    return "⚠️ Análise indisponível no momento."


# ── Main function ─────────────────────────────────────────────────────────────

def generate_analysis(data: dict[str, dict]) -> dict[str, str]:
    """
    Returns dict[display_name → full message text].
    Each message = deterministic header + AI analysis paragraph.
    """
    results = {}

    for name, commodity_data in data.items():
        logger.info(f"Generating analysis for {name}...")

        header = _build_header(name, commodity_data["cot"], commodity_data["price"])

        data_block = _build_data_block(name, commodity_data["cot"], commodity_data["price"])

        prompt = f"""Você é um analista sênior de mercados agrícolas. Com base nos dados abaixo do relatório COT (CFTC), referentes à posição de fundos gestores (Managed Money) em futuros e opções, escreva um parágrafo de análise em português brasileiro para envio via Telegram.

INSTRUÇÕES:
- Escreva 4 a 6 linhas, tom objetivo e profissional.
- Identifique se os fundos estão comprados ou vendidos e a direção recente do movimento.
- Indique se o posicionamento está em nível extremo (percentil alto ou baixo).
- Relacione a posição dos fundos com o comportamento do preço: convergência ou divergência.
- Não repita os números brutos — interprete-os.
- Use um emoji no início: 🟢 posição/tendência positiva, 🔴 negativa, 🟡 neutra/mista.
- NÃO inclua o nome da commodity no texto — ele já aparece no cabeçalho.

DADOS:
{data_block}

Escreva apenas o parágrafo, sem títulos adicionais ou comentários."""

        analysis = _call_groq(prompt)
        results[name] = f"{header}\n\n{analysis}"
        logger.info(f"  → Analysis done for {name}")

        time.sleep(1.0)   # avoid Groq rate limit across 9 sequential calls

    return results
