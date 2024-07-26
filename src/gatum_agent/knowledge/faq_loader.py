from pathlib import Path


class KnowledgeBase:
    """Simple markdown FAQ loader with keyword search (no vector DB required for prototype)."""

    def __init__(self, faq_dir: Path) -> None:
        self.faq_dir = faq_dir
        self._docs: list[tuple[str, str]] = []
        self._load()

    def _load(self) -> None:
        if not self.faq_dir.exists():
            return
        for path in sorted(self.faq_dir.glob("*.md")):
            self._docs.append((path.stem, path.read_text(encoding="utf-8")))

    def search(self, query: str, limit: int = 2) -> list[tuple[str, str]]:
        query_lower = query.lower()
        tokens = [t for t in query_lower.split() if len(t) > 2]
        scored: list[tuple[int, str, str]] = []
        for title, body in self._docs:
            text = f"{title} {body}".lower()
            score = sum(1 for t in tokens if t in text)
            if score > 0:
                scored.append((score, title, body))
        scored.sort(key=lambda x: -x[0])
        return [(t, b) for _, t, b in scored[:limit]]

    def format_answer(self, query: str) -> str | None:
        hits = self.search(query)
        if not hits:
            return None
        parts = []
        for title, body in hits:
            parts.append(f"**{title.replace('_', ' ').title()}**\n\n{body.strip()}")
        return "\n\n---\n\n".join(parts)
