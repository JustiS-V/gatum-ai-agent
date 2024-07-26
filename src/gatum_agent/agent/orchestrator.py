from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from gatum_agent.agent.classifier import IntentClassifier
from gatum_agent.agent.handlers import AgentResponse, ScenarioHandlers
from gatum_agent.agent.session import ConversationSession
from gatum_agent.config import settings
from gatum_agent.knowledge.faq_loader import KnowledgeBase
from gatum_agent.llm.client import LLMClient
from gatum_agent.models.ticket import Category, Channel, Priority, Ticket
from gatum_agent.storage.sqlite import TicketStore


class SupportAgent:
    def __init__(self, store: TicketStore, kb: KnowledgeBase) -> None:
        self.store = store
        self.kb = kb
        self.llm = LLMClient()
        self.classifier = IntentClassifier(self.llm)
        self.handlers = ScenarioHandlers(kb)
        self._sessions: dict[str, ConversationSession] = {}

    def _session_key(self, channel: Channel, client_id: str) -> str:
        return f"{channel.value}:{client_id}"

    def get_session(self, channel: Channel, client_id: str) -> ConversationSession:
        key = self._session_key(channel, client_id)
        if key not in self._sessions:
            self._sessions[key] = ConversationSession(
                client_id=client_id, channel=channel.value
            )
        return self._sessions[key]

    def is_after_hours(self) -> bool:
        tz = ZoneInfo(settings.business_tz)
        now = datetime.now(tz)
        if now.weekday() >= 5:
            return True
        return not (settings.business_start_hour <= now.hour < settings.business_end_hour)

    async def _notify_support_lead(self, ticket: Ticket) -> None:
        url = settings.support_lead_webhook_url
        if not url:
            return
        payload = {
            "event": "high_priority_feedback",
            "ticket_id": ticket.ticket_id,
            "summary": ticket.summary,
            "sentiment": ticket.sentiment.value,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)

    def process_message(
        self, channel: Channel, client_id: str, message: str
    ) -> AgentResponse:
        session = self.get_session(channel, client_id)
        session.add("user", message)

        if session.pending_intent:
            intent = session.pending_intent
        else:
            intent = self.classifier.classify(message, session.snippet())

        if (
            settings.after_hours_check_enabled
            and self.is_after_hours()
            and intent not in ("outage",)
        ):
            ticket = Ticket(
                channel=channel,
                client_id=client_id,
                category=Category.AFTER_HOURS,
                priority=Priority.NORMAL,
                summary="Звернення поза робочим часом",
                conversation_snippet=session.snippet(),
                escalation_target="morning_queue",
                resolved_by_ai=False,
                sentiment=self.handlers.detect_sentiment(message),
                metadata={"original_intent": intent, "message": message[:500]},
            )
            self.store.save(ticket)
            reply = (
                "Ми отримали ваше повідомлення і відповімо, щойно команда вийде на зв'язок. "
                f"Тікет #{ticket.ticket_id[:8]} створено."
            )
            session.add("assistant", reply)
            return AgentResponse(reply=reply, ticket=ticket)

        handler_map = {
            "how_to": self.handlers.handle_how_to,
            "billing": self.handlers.handle_billing,
            "delivery_issue": self.handlers.handle_delivery,
            "commercial": self.handlers.handle_commercial,
            "outage": self.handlers.handle_outage,
            "feedback": self.handlers.handle_feedback,
            "unknown": self.handlers.handle_unknown,
        }
        handler = handler_map.get(intent, self.handlers.handle_unknown)
        result: AgentResponse = handler(session, message, channel)

        if result.ticket:
            result.ticket.conversation_snippet = session.snippet()
            self.store.save(result.ticket)

        session.add("assistant", result.reply)
        return result

    async def process_message_async(
        self, channel: Channel, client_id: str, message: str
    ) -> AgentResponse:
        result = self.process_message(channel, client_id, message)
        if result.notify_support_lead and result.ticket:
            await self._notify_support_lead(result.ticket)
        return result
