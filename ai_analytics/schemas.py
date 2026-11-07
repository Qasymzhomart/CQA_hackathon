from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class AICriterionResult(BaseModel):
    criterion_id: str
    applicable: bool
    answer: str
    score: Optional[float]
    reason: str = Field(min_length=1)
    evidence_ids: list[str]
    checked_message_ids: list[str]
    critical_error: bool


class AIEvaluation(BaseModel):
    conversation_id: str
    criteria: list[AICriterionResult]


class UsageInfo(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 1
    estimated_cost_usd: float = 0.0
