from typing import Literal, Optional
from pydantic import BaseModel, Field


Language = Literal["RU", "KZ", "EN"]
Channel = Literal["agent_chat", "voice_call"]


class Utterance(BaseModel):
    timestamp: str
    speaker: str
    text: str
    message_id: Optional[str] = None


class Conversation(BaseModel):
    conversation_id: str
    channel: Channel
    language: Language
    transcript: list[Utterance]
    audio_url: Optional[str] = None


class Criterion(BaseModel):
    id: str
    name: str
    description: str = ""
    weight: float = Field(ge=0, le=100)
    response_type: Literal["binary", "scale", "flag"] = "binary"
    allow_na: bool = True
    scale_max: float = 1.0
    allowed_values: Optional[list[float]] = None


class CriterionResult(BaseModel):
    criterion_id: str
    answer: str
    raw_score: float = Field(ge=0)
    explanation: str
    evidence: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    checked_message_ids: list[str] = Field(default_factory=list)
    critical_error: bool = False
    na: bool = False
    na_reason: Optional[str] = None


class EvaluationRequest(BaseModel):
    conversation_id: str
    results: list[CriterionResult]


class AppealRequest(BaseModel):
    evaluation_id: str
    criterion_id: str
    comment: str


class ReviewRequest(BaseModel):
    evaluation_id: str
    criterion_id: str
    confirmed_score: float = Field(ge=0)
    reviewer_comment: str = ""
