from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from gatum_agent.config import settings
from gatum_agent.models.ticket import Ticket
from gatum_agent.storage.sqlite import TicketStore


def generate_report(store: TicketStore, fmt: str = "text") -> str:
    tickets = store.list_all()
    if fmt == "json":
        import json

        return json.dumps(build_report_dict(tickets), ensure_ascii=False, indent=2)
    if fmt == "markdown":
        return _format_markdown(build_report_dict(tickets))
    return _format_text(build_report_dict(tickets))


def build_report_dict(tickets: list[Ticket]) -> dict:
    total = len(tickets)
    by_channel: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_sentiment: Counter[str] = Counter()
    by_hour_bucket: Counter[str] = Counter()
    escalated = 0
    resolved_ai = 0
    after_hours = 0

    tz = ZoneInfo(settings.business_tz)

    for t in tickets:
        by_channel[t.channel.value] += 1
        by_category[t.category.value] += 1
        by_sentiment[t.sentiment.value] += 1
        created = t.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        else:
            created = created.astimezone(tz)
        by_hour_bucket[created.strftime("%Y-%m-%d %H:00")] += 1
        if t.escalation_target:
            escalated += 1
        if t.resolved_by_ai:
            resolved_ai += 1
        if created.weekday() >= 5 or not (
            settings.business_start_hour <= created.hour < settings.business_end_hour
        ):
            after_hours += 1

    pct_escalation = round(100 * escalated / total, 1) if total else 0.0
    pct_resolved = round(100 * resolved_ai / total, 1) if total else 0.0

    return {
        "total_tickets": total,
        "by_channel": dict(by_channel),
        "by_category": dict(by_category),
        "by_sentiment": dict(by_sentiment),
        "by_time_bucket": dict(sorted(by_hour_bucket.items())),
        "escalation_percent": pct_escalation,
        "ai_resolution_percent": pct_resolved,
        "after_hours_count": after_hours,
    }


def _format_text(data: dict) -> str:
    lines = [
        "=" * 50,
        "GATUM SUPPORT AGENT — ANALYTICS REPORT",
        "=" * 50,
        f"Total tickets: {data['total_tickets']}",
        "",
        "By channel:",
    ]
    for ch, n in data["by_channel"].items():
        lines.append(f"  {ch}: {n}")
    lines.extend(["", "By category:"])
    for cat, n in data["by_category"].items():
        lines.append(f"  {cat}: {n}")
    lines.extend(
        [
            "",
            f"Escalation rate: {data['escalation_percent']}%",
            f"AI resolution rate: {data['ai_resolution_percent']}%",
            "",
            "Sentiment distribution:",
        ]
    )
    for s, n in data["by_sentiment"].items():
        lines.append(f"  {s}: {n}")
    lines.append(f"\nAfter-hours tickets (outside 09:00–18:00): {data['after_hours_count']}")
    lines.append("=" * 50)
    return "\n".join(lines)


def _format_markdown(data: dict) -> str:
    lines = ["# Analytics Report", "", f"**Total tickets:** {data['total_tickets']}", ""]
    lines.append("## By channel\n| Channel | Count |\n|---------|-------|")
    for ch, n in data["by_channel"].items():
        lines.append(f"| {ch} | {n} |")
    lines.append("\n## By category\n| Category | Count |\n|----------|-------|")
    for cat, n in data["by_category"].items():
        lines.append(f"| {cat} | {n} |")
    lines.extend(
        [
            "",
            f"- **Escalation rate:** {data['escalation_percent']}%",
            f"- **AI resolution rate:** {data['ai_resolution_percent']}%",
            f"- **After-hours tickets:** {data['after_hours_count']}",
        ]
    )
    return "\n".join(lines)
