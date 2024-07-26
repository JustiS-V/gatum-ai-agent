from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gatum_agent.agent.orchestrator import SupportAgent
from gatum_agent.analytics.report import generate_report
from gatum_agent.config import settings
from gatum_agent.knowledge.faq_loader import KnowledgeBase
from gatum_agent.models.ticket import Channel
from gatum_agent.storage.sqlite import TicketStore

store: TicketStore | None = None
agent: SupportAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, agent
    store = TicketStore(settings.db_path)
    kb = KnowledgeBase(settings.faq_path)
    agent = SupportAgent(store, kb)
    yield


app = FastAPI(
    title="Gatum AI Support Agent",
    description="Multichannel support agent prototype",
    version="0.1.0",
    lifespan=lifespan,
)


class InboundMessage(BaseModel):
    client_id: str = Field(..., description="Client identifier in the channel")
    message: str = Field(..., min_length=1)
    metadata: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    reply: str
    ticket_id: str | None = None
    escalation_target: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "llm": bool(settings.openai_api_key)}


@app.post("/channels/{channel}/messages", response_model=MessageResponse)
async def inbound_message(channel: str, body: InboundMessage):
    try:
        ch = Channel(channel.lower())
    except ValueError as exc:
        raise HTTPException(400, f"Unknown channel: {channel}") from exc
    if ch == Channel.TELEGRAM:
        raise HTTPException(
            400,
            "Use Telegram bot for telegram channel; this endpoint is for zendesk/teams/whatsapp",
        )
    assert agent is not None
    result = await agent.process_message_async(ch, body.client_id, body.message)
    ticket = result.ticket
    return MessageResponse(
        reply=result.reply,
        ticket_id=ticket.ticket_id if ticket else None,
        escalation_target=ticket.escalation_target if ticket else None,
    )


@app.get("/tickets")
def list_tickets():
    assert store is not None
    return [t.model_dump(mode="json") for t in store.list_all()]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    assert store is not None
    ticket = store.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket.model_dump(mode="json")


@app.get("/analytics")
def analytics(format: str = "json"):
    assert store is not None
    if format not in ("json", "text", "markdown"):
        raise HTTPException(400, "format must be json, text, or markdown")
    if format == "json":
        from gatum_agent.analytics.report import build_report_dict

        return build_report_dict(store.list_all())
    return {"report": generate_report(store, fmt=format)}
