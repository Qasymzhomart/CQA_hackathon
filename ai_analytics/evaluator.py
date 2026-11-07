from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from . import DEFAULT_MODEL, PROMPT_VERSION
from .cost import estimate_cost_usd
from .prompt import SYSTEM_PROMPT, build_task
from .schemas import AIEvaluation, UsageInfo
from .validator import validate_ai_evaluation


@dataclass
class EvaluationRun:
    evaluation: AIEvaluation
    usage: UsageInfo
    prompt_version: str
    retry_count: int
    latency_ms: int


def _call_model(
    client: OpenAI,
    model: str,
    system_prompt: str,
    task: str,
) -> tuple[AIEvaluation, int, int]:
    completion = client.chat.completions.parse(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ],
        response_format=AIEvaluation,
    )
    message = completion.choices[0].message
    if message.parsed is None:
        raise ValueError("Model did not return a parseable structured evaluation")

    usage = completion.usage
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return message.parsed, input_tokens, output_tokens


def evaluate_conversation(
    conversation: dict[str, Any],
    criteria: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: OpenAI | None = None,
) -> EvaluationRun:
    """Run one structured CQA evaluation with at most one validation retry."""
    model = model or os.getenv("CQA_AI_MODEL", DEFAULT_MODEL)
    client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    task = build_task(conversation, criteria)
    start = time.perf_counter()

    total_input_tokens = 0
    total_output_tokens = 0
    retry_count = 0

    evaluation, input_tokens, output_tokens = _call_model(
        client, model, SYSTEM_PROMPT, task
    )
    total_input_tokens += input_tokens
    total_output_tokens += output_tokens

    errors = validate_ai_evaluation(evaluation, conversation, criteria)

    if errors:
        retry_count = 1
        retry_task = (
            task
            + "\n\nYour previous response was invalid.\n"
            + "Validation errors:\n- "
            + "\n- ".join(errors)
            + "\nReturn a corrected structured response only. "
              "Do not change valid results unless required."
            + "\nPrevious response:\n"
            + json.dumps(evaluation.model_dump(), ensure_ascii=False)
        )

        evaluation, input_tokens, output_tokens = _call_model(
            client, model, SYSTEM_PROMPT, retry_task
        )
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        errors = validate_ai_evaluation(evaluation, conversation, criteria)
        if errors:
            raise ValueError(
                "AI evaluation failed validation after retry: "
                + "; ".join(errors)
            )

    latency_ms = round((time.perf_counter() - start) * 1000)
    usage = UsageInfo(
        model=model,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        calls=1 + retry_count,
        estimated_cost_usd=estimate_cost_usd(
            total_input_tokens, total_output_tokens
        ),
    )

    return EvaluationRun(
        evaluation=evaluation,
        usage=usage,
        prompt_version=PROMPT_VERSION,
        retry_count=retry_count,
        latency_ms=latency_ms,
    )
