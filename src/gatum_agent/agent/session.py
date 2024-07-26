from dataclasses import dataclass, field


@dataclass
class ConversationSession:
    client_id: str
    channel: str
    history: list[tuple[str, str]] = field(default_factory=list)
    pending_intent: str | None = None
    collected_fields: dict[str, str] = field(default_factory=dict)

    def add(self, role: str, text: str) -> None:
        self.history.append((role, text))

    def snippet(self, max_exchanges: int = 5) -> str:
        lines = []
        for role, text in self.history[-max_exchanges * 2 :]:
            prefix = "Client" if role == "user" else "Agent"
            lines.append(f"{prefix}: {text[:300]}")
        return "\n".join(lines)
