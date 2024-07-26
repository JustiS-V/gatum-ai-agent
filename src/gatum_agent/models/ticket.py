from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Channel(str, Enum):
    ZENDESK = "zendesk"
    TELEGRAM = "telegram"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"


class Category(str, Enum):
    HOW_TO = "how_to"
    BILLING = "billing"
    DELIVERY_ISSUE = "delivery_issue"
    AFTER_HOURS = "after_hours"
    COMMERCIAL = "commercial"
    OUTAGE = "outage"
    UNKNOWN = "unknown"
    FEEDBACK = "feedback"
    OTHER = "other"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EscalationTarget(str, Enum):
    FINANCE = "finance"
    SALES = "sales"
    L2_SUPPORT = "l2_support"
    SUPPORT_LEAD = "support_lead"
    MORNING_QUEUE = "morning_queue"


class Ticket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    channel: Channel
    client_id: str
    category: Category
    priority: Priority = Priority.NORMAL
    summary: str = Field(max_length=200)
    conversation_snippet: str = ""
    escalation_target: str | None = None
    resolved_by_ai: bool = False
    sentiment: Sentiment = Sentiment.NEUTRAL
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_db_row(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "created_at": self.created_at.isoformat(),
            "channel": self.channel.value,
            "client_id": self.client_id,
            "category": self.category.value,
            "priority": self.priority.value,
            "summary": self.summary[:200],
            "conversation_snippet": self.conversation_snippet,
            "escalation_target": self.escalation_target,
            "resolved_by_ai": int(self.resolved_by_ai),
            "sentiment": self.sentiment.value,
            "metadata": self.metadata,
        }
