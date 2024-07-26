from openai import OpenAI

from gatum_agent.config import settings


class LLMClient:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    def classify_intent(self, message: str, context: str = "") -> str | None:
        if not self._client:
            return None
        prompt = (
            "Classify the customer message into exactly one intent label:\n"
            "how_to, billing, delivery_issue, commercial, outage, feedback, unknown\n\n"
            f"Context:\n{context}\n\nMessage:\n{message}\n\n"
            "Reply with only the label."
        )
        resp = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=20,
        )
        label = (resp.choices[0].message.content or "").strip().lower()
        return label.split()[0] if label else None

    def refine_reply(self, system: str, user: str) -> str | None:
        if not self._client:
            return None
        resp = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        return resp.choices[0].message.content
