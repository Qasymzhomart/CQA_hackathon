from __future__ import annotations

import os


def _rate(name: str) -> float:
    """Read per-million-token price from env.

    Defaults to zero so a free-tier hackathon key is never reported as paid.
    Set CQA_AI_INPUT_USD_PER_M and CQA_AI_OUTPUT_USD_PER_M when using a paid tier.
    """
    return float(os.getenv(name, "0") or 0)


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    input_rate = _rate("CQA_AI_INPUT_USD_PER_M")
    output_rate = _rate("CQA_AI_OUTPUT_USD_PER_M")
    return round(
        input_tokens / 1_000_000 * input_rate
        + output_tokens / 1_000_000 * output_rate,
        8,
    )
