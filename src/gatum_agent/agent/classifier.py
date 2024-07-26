import re

from gatum_agent.llm.client import LLMClient


INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("billing", [r"баланс", r"поповн", r"wallet", r"реквізит", r"оплат", r"payment", r"deposit"]),
    (
        "delivery_issue",
        [r"не достав", r"недостав", r"delivery", r"не прийшл", r"не дошл", r"failed sms"],
    ),
    ("commercial", [r"цін", r"знижк", r"тариф", r"price", r"discount", r"комерц", r"договор"]),
    (
        "outage",
        [r"збій", r"помилк", r"error", r"down", r"smpp", r"api", r"не працю", r"впал"],
    ),
    (
        "how_to",
        [r"як ", r"how to", r"де подив", r"інструкц", r"розсил", r"campaign", r"delivery report"],
    ),
    (
        "feedback",
        [r"скарг", r"жахлив", r"поган", r"незадовол", r"complaint", r"terrible", r"worst"],
    ),
]


class IntentClassifier:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def classify(self, message: str, context: str = "") -> str:
        text = message.lower()
        for intent, patterns in INTENT_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return intent
        llm_intent = self.llm.classify_intent(message, context)
        if llm_intent in {i for i, _ in INTENT_PATTERNS} | {"unknown", "feedback"}:
            return llm_intent
        return "unknown"
