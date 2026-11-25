"""Orchestration pipeline for AI comment generation, validation, retry, and scoring."""

import json
import re
from typing import Sequence

from pydantic import ValidationError

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.providers import AIProvider, AIProviderError, resolve_ai_provider
from app.ai.quality import (
    detect_excluded_topic,
    detect_sensitive_content,
    score_draft,
)
from app.ai.schemas import AIGenerationResult, DraftPipelineOutput, ScoredDraft
from app.core.config import Settings


def _extract_json_object(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_ai_response(raw: str) -> AIGenerationResult:
    cleaned = _extract_json_object(raw)
    data = json.loads(cleaned)
    return AIGenerationResult.model_validate(data)


class CommentEngine:
    def __init__(self, settings: Settings, provider: AIProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider or resolve_ai_provider(settings)

    async def generate_drafts(
        self,
        *,
        platform: str,
        author_name: str,
        content_text: str,
        media_type: str = "text",
        tone: str = "professional-conversational",
        length: str = "short",
        language: str = "English",
        emoji_level: str = "low",
        relevance_threshold: float = 0.70,
        variants: int = 2,
        preferred_topics: Sequence[str] = (),
        excluded_topics: Sequence[str] = (),
        avoid_phrases: Sequence[str] = (),
        style_samples: Sequence[str] = (),
        recent_comments: Sequence[str] = (),
        custom_instruction: str | None = None,
    ) -> DraftPipelineOutput:
        clean_content = (content_text or "").strip()
        if not clean_content:
            return DraftPipelineOutput(
                should_skip=True,
                skip_reason="Post has no text content or preview to respond to.",
                topic="missing-context",
                relevance_score=0.0,
                model_used=self.provider.name,
                drafts=[],
            )

        matched_excluded = detect_excluded_topic(clean_content, excluded_topics)
        if matched_excluded:
            return DraftPipelineOutput(
                should_skip=True,
                skip_reason=f"Skipped because post matches excluded topic: '{matched_excluded}'.",
                topic=matched_excluded,
                relevance_score=0.15,
                model_used=self.provider.name,
                drafts=[],
            )

        if detect_sensitive_content(clean_content):
            return DraftPipelineOutput(
                should_skip=True,
                skip_reason="Post appears to contain sensitive personal news; skipped for human judgment.",
                topic="sensitive-personal",
                relevance_score=0.35,
                model_used=self.provider.name,
                drafts=[],
            )

        user_prompt = build_user_prompt(
            platform=platform,
            author_name=author_name,
            content_text=clean_content,
            media_type=media_type,
            tone=tone,
            length=length,
            language=language,
            emoji_level=emoji_level,
            variants=variants,
            preferred_topics=preferred_topics,
            excluded_topics=excluded_topics,
            avoid_phrases=avoid_phrases,
            style_samples=style_samples,
            recent_comments=recent_comments,
            custom_instruction=custom_instruction,
        )

        parsed: AIGenerationResult | None = None
        fallback_used = False

        # Up to 2 attempts (initial + 1 retry on malformed JSON/schema per AI_COMMENT_ENGINE.md)
        for attempt in range(2):
            try:
                prompt_to_send = (
                    user_prompt
                    if attempt == 0
                    else user_prompt + "\nIMPORTANT: Return ONLY valid JSON matching the schema."
                )
                raw = await self.provider.generate_json(SYSTEM_PROMPT, prompt_to_send)
                parsed = parse_ai_response(raw)
                break
            except (json.JSONDecodeError, ValidationError, AIProviderError):
                if attempt == 1:
                    fallback_used = True
                    return DraftPipelineOutput(
                        should_skip=True,
                        skip_reason="AI generation failed output validation after retry; recorded safe skip.",
                        topic="generation-error",
                        relevance_score=0.0,
                        model_used=self.provider.name,
                        drafts=[],
                        fallback_used=True,
                    )

        assert parsed is not None

        if parsed.should_skip or not parsed.drafts:
            return DraftPipelineOutput(
                should_skip=True,
                skip_reason=parsed.skip_reason or "Post deemed not relevant enough for a comment draft.",
                topic=parsed.topic,
                relevance_score=round(parsed.relevance_score, 2),
                model_used=self.provider.name,
                drafts=[],
                fallback_used=fallback_used,
            )

        if parsed.relevance_score < relevance_threshold:
            return DraftPipelineOutput(
                should_skip=True,
                skip_reason=(
                    f"Relevance score ({parsed.relevance_score:.2f}) is below your "
                    f"configured threshold ({relevance_threshold:.2f})."
                ),
                topic=parsed.topic,
                relevance_score=round(parsed.relevance_score, 2),
                model_used=self.provider.name,
                drafts=[],
                fallback_used=fallback_used,
            )

        scored: list[ScoredDraft] = []
        for option in parsed.drafts[:variants]:
            q_score, breakdown, rep_sim, warnings = score_draft(
                post_text=clean_content,
                draft_text=option.text,
                relevance_score=parsed.relevance_score,
                length_pref=length,
                emoji_level=emoji_level,
                avoid_phrases=avoid_phrases,
                recent_comments=recent_comments,
                style_samples=style_samples,
            )
            scored.append(
                ScoredDraft(
                    style=option.style,
                    text=option.text.strip(),
                    relevance_score=round(parsed.relevance_score, 2),
                    quality_score=q_score,
                    quality_breakdown=breakdown,
                    repetition_similarity=rep_sim,
                    below_threshold=q_score < relevance_threshold,
                    warnings=warnings,
                )
            )

        return DraftPipelineOutput(
            should_skip=False,
            skip_reason=None,
            topic=parsed.topic,
            relevance_score=round(parsed.relevance_score, 2),
            model_used=self.provider.name,
            drafts=scored,
            fallback_used=fallback_used,
        )
