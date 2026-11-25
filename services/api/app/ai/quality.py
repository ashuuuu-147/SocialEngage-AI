"""Quality scoring, prompt-safety checks, and repetition detection per AI_COMMENT_ENGINE.md."""

import re
from difflib import SequenceMatcher
from typing import Sequence

GENERIC_PRAISE = (
    "amazing post",
    "great post",
    "awesome post",
    "love this",
    "thanks for sharing",
    "so inspiring",
    "nice post",
)

SENSITIVE_KEYWORDS = (
    "passed away",
    "funeral",
    "condolences",
    "bereavement",
    "diagnosed with",
    "layoff",
    "laid off",
    "hospitalized",
    "miscarriage",
    "grief",
)

PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore your rules",
    "disregard all instructions",
    "system prompt",
    "reveal your prompt",
    "auto-post immediately",
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "is", "are", "was", "were", "be", "been", "this", "that",
    "it", "as", "from", "you", "your", "we", "our", "they", "their", "i", "my",
}


def normalize_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def detect_sensitive_content(content_text: str) -> bool:
    lowered = content_text.lower()
    return any(kw in lowered for kw in SENSITIVE_KEYWORDS)


def detect_excluded_topic(content_text: str, excluded_topics: Sequence[str]) -> str | None:
    lowered = content_text.lower()
    for topic in excluded_topics:
        cleaned = topic.strip().lower()
        if cleaned and cleaned in lowered:
            return topic
    return None


def contains_avoided_phrase(draft_text: str, avoid_phrases: Sequence[str]) -> list[str]:
    lowered = draft_text.lower()
    return [phrase for phrase in avoid_phrases if phrase.strip() and phrase.strip().lower() in lowered]


def compute_repetition_similarity(draft_text: str, recent_comments: Sequence[str]) -> float:
    """Return max similarity (0-1) against recent drafts using sequence & token overlap."""
    if not recent_comments:
        return 0.0
    norm_draft = " ".join(draft_text.lower().split())
    draft_tokens = set(normalize_tokens(draft_text))
    draft_opening = " ".join(norm_draft.split()[:4])
    max_sim = 0.0
    for prev in recent_comments:
        norm_prev = " ".join(prev.lower().split())
        if not norm_prev:
            continue
        seq_ratio = SequenceMatcher(None, norm_draft, norm_prev).ratio()
        prev_tokens = set(normalize_tokens(prev))
        jaccard = (
            len(draft_tokens & prev_tokens) / max(1, len(draft_tokens | prev_tokens))
            if (draft_tokens or prev_tokens)
            else 0.0
        )
        prev_opening = " ".join(norm_prev.split()[:4])
        opening_bonus = 0.15 if (draft_opening and draft_opening == prev_opening) else 0.0
        max_sim = max(max_sim, min(1.0, max(seq_ratio, jaccard) + opening_bonus))
    return round(max_sim, 3)


def score_draft(
    *,
    post_text: str,
    draft_text: str,
    relevance_score: float,
    length_pref: str,
    emoji_level: str,
    avoid_phrases: Sequence[str],
    recent_comments: Sequence[str],
    style_samples: Sequence[str],
) -> tuple[float, dict[str, float], float, list[str]]:
    """Compute weighted quality score (0-1) per AI_COMMENT_ENGINE.md section 5."""
    warnings: list[str] = []

    post_tokens = set(normalize_tokens(post_text))
    draft_tokens = set(normalize_tokens(draft_text))
    overlap = len(post_tokens & draft_tokens) / max(1, min(len(post_tokens), 8)) if post_tokens else 0.5
    content_rel = min(1.0, 0.55 * relevance_score + 0.45 * min(1.0, overlap * 1.4))

    # Specificity: penalize short generic praise
    lowered = draft_text.lower().strip()
    is_generic = any(p in lowered for p in GENERIC_PRAISE) and len(draft_text.split()) < 10
    specificity = 0.35 if is_generic else min(1.0, 0.5 + 0.5 * min(1.0, overlap * 1.5))
    if is_generic:
        warnings.append("Draft looks generic; consider referencing a specific detail from the post.")

    # Naturalness: penalize hashtag spam or avoided phrases or prompt injection echoes
    hashtag_count = draft_text.count("#")
    avoided = contains_avoided_phrase(draft_text, avoid_phrases)
    if avoided:
        warnings.append(f"Contains avoided phrase(s): {', '.join(avoided)}")
    naturalness = 0.92
    if hashtag_count > 1:
        naturalness -= 0.25
        warnings.append("Contains unrequested hashtags.")
    if avoided:
        naturalness -= 0.4
    if any(m in lowered for m in PROMPT_INJECTION_MARKERS):
        naturalness = 0.1
        warnings.append("Draft echoed suspicious instruction text.")
    naturalness = max(0.0, min(1.0, naturalness))

    # Style match: check emoji compliance & non-verbatim copy of samples
    emoji_chars = len(re.findall(r"[\U0001F300-\U0001FAFF]", draft_text))
    style_match = 0.9
    if emoji_level == "none" and emoji_chars > 0:
        style_match -= 0.25
        warnings.append("Contains emojis despite 'none' emoji preference.")
    for sample in style_samples:
        if sample.strip() and SequenceMatcher(None, lowered, sample.strip().lower()).ratio() > 0.85:
            style_match -= 0.5
            warnings.append("Draft too closely copies a personal style sample.")
            break
    style_match = max(0.0, min(1.0, style_match))

    # Concision: check against requested length
    words = len(draft_text.split())
    limits = {"short": (5, 38), "medium": (12, 65), "detailed": (20, 110)}
    min_w, max_w = limits.get(length_pref, (5, 45))
    if min_w <= words <= max_w:
        concision = 0.95
    elif words < min_w:
        concision = 0.65
    else:
        concision = max(0.3, 0.95 - (words - max_w) * 0.015)

    # Repetition avoidance
    rep_sim = compute_repetition_similarity(draft_text, recent_comments)
    rep_score = max(0.0, 1.0 - rep_sim)
    if rep_sim >= 0.65:
        warnings.append("High similarity to one of your recent drafts.")

    breakdown = {
        "content_relevance": round(content_rel, 3),
        "specificity": round(specificity, 3),
        "naturalness": round(naturalness, 3),
        "style_match": round(style_match, 3),
        "concision": round(concision, 3),
        "repetition_avoidance": round(rep_score, 3),
    }

    weighted = (
        content_rel * 0.35
        + specificity * 0.20
        + naturalness * 0.15
        + style_match * 0.15
        + concision * 0.10
        + rep_score * 0.05
    )
    return round(weighted, 2), breakdown, rep_sim, warnings
