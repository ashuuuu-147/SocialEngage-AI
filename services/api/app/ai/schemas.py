"""AI Comment Engine schemas and structured validation."""

from typing import Optional

from pydantic import BaseModel, Field


class AIDraftOption(BaseModel):
    style: str = Field(..., min_length=2, max_length=40)
    text: str = Field(..., min_length=4, max_length=1200)


class AIGenerationResult(BaseModel):
    should_skip: bool = False
    skip_reason: Optional[str] = None
    topic: str = Field(default="general", max_length=100)
    relevance_score: float = Field(default=0.75, ge=0.0, le=1.0)
    drafts: list[AIDraftOption] = Field(default_factory=list)


class ScoredDraft(BaseModel):
    style: str
    text: str
    relevance_score: float
    quality_score: float
    quality_breakdown: dict[str, float]
    repetition_similarity: float
    below_threshold: bool
    warnings: list[str] = Field(default_factory=list)


class DraftPipelineOutput(BaseModel):
    should_skip: bool
    skip_reason: Optional[str]
    topic: str
    relevance_score: float
    model_used: str
    drafts: list[ScoredDraft]
    fallback_used: bool = False
