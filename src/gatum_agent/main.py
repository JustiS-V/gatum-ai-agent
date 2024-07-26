import argparse
import asyncio
import logging
import sys
from pathlib import Path

import uvicorn

# Allow running without package install
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gatum_agent.agent.orchestrator import SupportAgent  # noqa: E402
from gatum_agent.analytics.report import generate_report  # noqa: E402
from gatum_agent.channels.telegram_bot import build_telegram_app  # noqa: E402
from gatum_agent.config import settings  # noqa: E402
from gatum_agent.knowledge.faq_loader import KnowledgeBase  # noqa: E402
from gatum_agent.storage.sqlite import TicketStore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run_analytics(fmt: str) -> None:
    store = TicketStore(settings.db_path)
    print(generate_report(store, fmt=fmt))


async def run_server() -> None:
    store = TicketStore(settings.db_path)
    kb = KnowledgeBase(settings.faq_path)
    agent = SupportAgent(store, kb)

    tg_app = build_telegram_app(agent)
    config = uvicorn.Config(
        "gatum_agent.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
    server = uvicorn.Server(config)

    async def serve_api():
        await server.serve()

    async def serve_telegram():
        if tg_app is None:
            return
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started")
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()

    tasks = [asyncio.create_task(serve_api())]
    if tg_app:
        tasks.append(asyncio.create_task(serve_telegram()))
    else:
        logger.info(
            "Webhook channels only (zendesk/teams/whatsapp via POST /channels/{channel}/messages)"
        )

    await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gatum AI Support Agent")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="Start API + Telegram bot")
    p_analytics = sub.add_parser("analytics", help="Print analytics report")
    p_analytics.add_argument(
        "--format", choices=["text", "json", "markdown"], default="text"
    )

    args = parser.parse_args()
    if args.command == "analytics":
        run_analytics(args.format)
    elif args.command == "run" or args.command is None:
        asyncio.run(run_server())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
