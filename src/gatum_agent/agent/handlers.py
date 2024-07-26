import re
from dataclasses import dataclass

from gatum_agent.config import settings
from gatum_agent.knowledge.faq_loader import KnowledgeBase
from gatum_agent.models.ticket import (
    Category,
    EscalationTarget,
    Priority,
    Sentiment,
    Ticket,
)
from gatum_agent.agent.session import ConversationSession


@dataclass
class AgentResponse:
    reply: str
    ticket: Ticket | None = None
    notify_support_lead: bool = False


class ScenarioHandlers:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def detect_sentiment(self, message: str) -> Sentiment:
        negative = [
            "жахлив",
            "поган",
            "злий",
            "незадовол",
            "скарг",
            "terrible",
            "angry",
            "worst",
            "bad service",
        ]
        positive = ["дякую", "чудово", "супер", "thanks", "great", "excellent"]
        lower = message.lower()
        if any(w in lower for w in negative):
            return Sentiment.NEGATIVE
        if any(w in lower for w in positive):
            return Sentiment.POSITIVE
        return Sentiment.NEUTRAL

    def handle_how_to(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        answer = self.kb.format_answer(message)
        if not answer:
            answer = (
                "Перегляньте документацію Gatum: https://docs.gatum.io (демо-посилання).\n"
                "Типові кроки: увійти → Кампанії → Нова розсилка → обрати маршрут → запустити."
            )
        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.HOW_TO,
            priority=Priority.LOW,
            summary="Питання щодо використання платформи",
            conversation_snippet=session.snippet(),
            escalation_target=None,
            resolved_by_ai=True,
            sentiment=self.detect_sentiment(message),
            metadata={"intent": "how_to"},
        )
        return AgentResponse(reply=answer, ticket=ticket)

    def handle_billing(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        wallet = settings.billing_wallet_address
        reply = (
            "Щоб поповнити баланс Gatum:\n"
            "1. Увійдіть у кабінет → Білінг → Поповнення.\n"
            f"2. Надішліть USDT (TRC-20) на гаманець: `{wallet}`\n"
            "3. Після оплати надішліть сюди TX hash або скрін підтвердження.\n\n"
            "Після отримання підтвердження фінансовий менеджер зарахує кошти."
        )
        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.BILLING,
            priority=Priority.NORMAL,
            summary="Запит на поповнення балансу",
            conversation_snippet=session.snippet(),
            escalation_target=EscalationTarget.FINANCE.value,
            resolved_by_ai=False,
            sentiment=Sentiment.NEUTRAL,
            metadata={"wallet": wallet, "awaiting_tx_proof": True},
        )
        if any(k in message.lower() for k in ("tx", "hash", "транзак", "скрін", "screenshot")):
            ticket.metadata["transaction_proof"] = message[:500]
            reply += "\n\nДякуємо! Передали дані транзакції фінансовому менеджеру."
        return AgentResponse(reply=reply, ticket=ticket)

    def handle_delivery(
        self, session: ConversationSession, message: str, channel
    ) -> AgentResponse:
        fields = session.collected_fields
        for label, patterns in [
            ("phone", [r"\+?\d{10,15}"]),
            ("time", [r"\d{1,2}[:.]\d{2}", r"\d{4}-\d{2}-\d{2}", r"вчора", r"сьогодні"]),
            ("sender_id", [r"sender", r"відправник", r"alpha"]),
        ]:
            if label not in fields:
                for p in patterns:
                    m = re.search(p, message, re.I)
                    if m:
                        fields[label] = m.group(0)
        if "route" not in fields and "маршрут" in message.lower():
            fields["route"] = message

        missing = [k for k in ("phone", "time") if k not in fields]
        if missing:
            reply = (
                "Для перевірки доставки SMS, будь ласка, надішліть:\n"
                "• номер телефону одержувача\n"
                "• час відправки\n"
                "• sender ID та маршрут (якщо відомі)"
            )
            session.pending_intent = "delivery_issue"
            return AgentResponse(reply=reply, ticket=None)

        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.DELIVERY_ISSUE,
            priority=Priority.HIGH,
            summary=f"Недоставка SMS на {fields.get('phone', '?')}",
            conversation_snippet=session.snippet(),
            escalation_target=EscalationTarget.L2_SUPPORT.value,
            resolved_by_ai=False,
            sentiment=Sentiment.NEUTRAL,
            metadata=dict(fields),
        )
        session.pending_intent = None
        reply = (
            "Дякуємо, дані отримано. Передали на L2 технічну підтримку для розслідування.\n"
            f"Тікет #{ticket.ticket_id[:8]}."
        )
        return AgentResponse(reply=reply, ticket=ticket)

    def handle_commercial(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        reply = (
            "Дякуємо за інтерес до комерційних умов Gatum. "
            "Менеджер з продажів зв'яжеться з вами найближчим часом. "
            "Ми не надаємо ціни в автоматичному режимі."
        )
        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.COMMERCIAL,
            priority=Priority.NORMAL,
            summary="Запит щодо цін або комерційних умов",
            conversation_snippet=session.snippet(),
            escalation_target=EscalationTarget.SALES.value,
            resolved_by_ai=False,
            sentiment=Sentiment.NEUTRAL,
            metadata={},
        )
        return AgentResponse(reply=reply, ticket=ticket)

    def handle_outage(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        fields = session.collected_fields
        for key, hints in [
            ("error_text", ["error", "помилк", "exception", "timeout"]),
            ("account", ["account", "акаунт", "login"]),
            ("ip", [r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"]),
        ]:
            if key not in fields and any(h in message.lower() for h in hints if not h.startswith("\\")):
                fields[key] = message[:300]

        if "error_text" not in fields:
            session.pending_intent = "outage"
            return AgentResponse(
                reply=(
                    "Розуміємо терміновість. Надішліть, будь ласка:\n"
                    "• текст помилки\n"
                    "• час виникнення\n"
                    "• акаунт або IP, що постраждав"
                ),
                ticket=None,
            )

        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.OUTAGE,
            priority=Priority.URGENT,
            summary="Збій платформи або API",
            conversation_snippet=session.snippet(),
            escalation_target=EscalationTarget.L2_SUPPORT.value,
            resolved_by_ai=False,
            sentiment=Sentiment.NEUTRAL,
            metadata=dict(fields),
        )
        session.pending_intent = None
        reply = (
            "Підтвердили терміновість. Ескалували на L2 технічну підтримку (високий пріоритет).\n"
            f"Тікет #{ticket.ticket_id[:8]}."
        )
        return AgentResponse(reply=reply, ticket=ticket)

    def handle_unknown(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        reply = (
            "Дякуємо за звернення. Ваш запит передано спеціалісту підтримки — "
            "ми не надаємо автоматичну відповідь на це питання."
        )
        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.UNKNOWN,
            priority=Priority.NORMAL,
            summary="Нерозпізнаний запит клієнта",
            conversation_snippet=session.snippet(),
            escalation_target="support_queue",
            resolved_by_ai=False,
            sentiment=Sentiment.NEUTRAL,
            metadata={"raw_message": message[:1000]},
        )
        return AgentResponse(reply=reply, ticket=ticket)

    def handle_feedback(self, session: ConversationSession, message: str, channel) -> AgentResponse:
        sentiment = self.detect_sentiment(message)
        priority = Priority.HIGH if sentiment == Sentiment.NEGATIVE else Priority.NORMAL
        reply = (
            "Дякуємо за ваш відгук — він дуже важливий для нас. "
            "Передали керівнику відділу підтримки для опрацювання."
        )
        ticket = Ticket(
            channel=channel,
            client_id=session.client_id,
            category=Category.FEEDBACK,
            priority=priority,
            summary="Відгук або скарга щодо якості обслуговування",
            conversation_snippet=session.snippet(),
            escalation_target=EscalationTarget.SUPPORT_LEAD.value,
            resolved_by_ai=False,
            sentiment=sentiment,
            metadata={"bonus_scenario": "C-8"},
        )
        return AgentResponse(
            reply=reply,
            ticket=ticket,
            notify_support_lead=sentiment == Sentiment.NEGATIVE,
        )
