"""AI provider abstraction (Gemini, OpenAI-compatible, and deterministic local mock)."""

import json
import re
from abc import ABC, abstractmethod

import httpx

from app.ai.quality import normalize_tokens
from app.core.config import Settings


class AIProviderError(Exception):
    """Raised when an AI provider call fails or times out."""


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return raw JSON string response from the underlying model."""


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.name = f"gemini:{model}"

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.6,
                "responseMimeType": "application/json",
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise AIProviderError(f"Gemini API error HTTP {resp.status_code}")
            data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Malformed Gemini response envelope") from exc


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 25.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.name = f"openai_compatible:{model}"

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise AIProviderError(f"AI API error HTTP {resp.status_code}")
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Malformed chat completions response") from exc


class MockAIProvider(AIProvider):
    """Safe, deterministic local fallback provider when external API keys are absent."""

    name = "mock-local-v1"

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        # Extract content strictly between <untrusted_social_post> tags
        match = re.search(
            r"<untrusted_social_post>(.*?)</untrusted_social_post>",
            user_prompt,
            re.DOTALL,
        )
        block = match.group(1) if match else user_prompt
        content_match = re.search(r"content:\s*(.*)", block, re.DOTALL)
        post_text = content_match.group(1).strip() if content_match else block.strip()

        variants_match = re.search(r"Generate\s+(\d+)\s+distinct", user_prompt)
        variants = int(variants_match.group(1)) if variants_match else 2
        variants = max(1, min(3, variants))

        tone_match = re.search(r"-\s*Tone:\s*(.+)", user_prompt)
        tone = tone_match.group(1).strip() if tone_match else "thoughtful"

        tokens = normalize_tokens(post_text)
        key_terms = tokens[:4] if tokens else ["this", "update"]
        topic = " ".join(key_terms[:2]).title() if key_terms else "Industry Insights"

        if len(post_text.split()) < 4:
            return json.dumps(
                {
                    "should_skip": False,
                    "skip_reason": None,
                    "topic": topic,
                    "relevance_score": 0.62,
                    "drafts": [
                        {
                            "style": "clarifying",
                            "text": "Interesting point—curious what sparked this perspective and how you're applying it right now?",
                        }
                    ][:variants],
                }
            )

        focus_phrase = " and ".join(key_terms[:2]) if len(key_terms) >= 2 else key_terms[0]
        is_achievement = any(
            w in post_text.lower()
            for w in ("launched", "milestone", "excited to share", "shipped", "promoted", "award")
        )

        if is_achievement:
            candidates = [
                {
                    "style": "warm-professional",
                    "text": f"Congratulations on the milestone with {focus_phrase}! Wishing your team continued momentum as this rolls out.",
                },
                {
                    "style": "curious",
                    "text": f"Big milestone on {focus_phrase}—what was the hardest trade-off you had to make getting it across the finish line?",
                },
                {
                    "style": "concise",
                    "text": f"Well earned on {focus_phrase}. Looking forward to seeing how it evolves from here.",
                },
            ]
        else:
            candidates = [
                {
                    "style": tone if len(tone) < 25 else "thoughtful",
                    "text": f"Your point on {focus_phrase} resonates—teams often underestimate how much clarity upfront saves rework later.",
                },
                {
                    "style": "question-led",
                    "text": f"Really grounded take on {focus_phrase}. Have you seen that approach hold up when priorities shift mid-quarter?",
                },
                {
                    "style": "concise",
                    "text": f"Helpful breakdown on {focus_phrase}, especially keeping the practical trade-offs front and center.",
                },
            ]

        return json.dumps(
            {
                "should_skip": False,
                "skip_reason": None,
                "topic": topic,
                "relevance_score": 0.84,
                "drafts": candidates[:variants],
            }
        )


def resolve_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
        )
    if (
        settings.ai_provider == "openai_compatible"
        and settings.ai_base_url
        and settings.ai_api_key
    ):
        return OpenAICompatibleProvider(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
        )
    return MockAIProvider()
