from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

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
    client: Any,
    model: str,
    system_prompt: str,
    task: str,
) -> tuple[AIEvaluation, int, int]:
    response = client.models.generate_content(
        model=model,
        contents=task,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=AIEvaluation,
        ),
    )

    parsed = response.parsed
    if parsed is None:
        raise ValueError("Gemini did not return a parseable structured evaluation")

    if isinstance(parsed, AIEvaluation):
        evaluation = parsed
    else:
        evaluation = AIEvaluation.model_validate(parsed)

    usage = getattr(response, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    return evaluation, input_tokens, output_tokens


def evaluate_conversation(
    conversation: dict[str, Any],
    criteria: list[dict[str, Any]],
    *,
    model: str | None = None,
    client: Any | None = None,
) -> EvaluationRun:
    """Run one Gemini structured CQA evaluation with one validation retry."""
    model = model or os.getenv("CQA_AI_MODEL", DEFAULT_MODEL)

    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        client = genai.Client(api_key=api_key)

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
