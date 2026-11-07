from __future__ import annotations

# GPT-5.4 Mini standard text-token pricing as published on the OpenAI model page
# when this hackathon implementation was prepared (2026-11-07).
# Re-check official pricing before the final presentation.
INPUT_USD_PER_M = 0.75
OUTPUT_USD_PER_M = 4.50


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * INPUT_USD_PER_M
        + output_tokens / 1_000_000 * OUTPUT_USD_PER_M,
        8,
    )
