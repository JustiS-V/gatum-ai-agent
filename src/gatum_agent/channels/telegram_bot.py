import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from gatum_agent.agent.orchestrator import SupportAgent
from gatum_agent.config import settings
from gatum_agent.models.ticket import Channel

logger = logging.getLogger(__name__)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вітаємо в Gatum Support Bot (демо).\n"
        "Напишіть питання — наприклад: «як зробити розсилку?» або «поповнити баланс»."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    agent: SupportAgent = context.application.bot_data["agent"]
    if not update.message or not update.effective_user:
        return
    client_id = str(update.effective_user.id)
    text = update.message.text or ""
    result = await agent.process_message_async(Channel.TELEGRAM, client_id, text)
    await update.message.reply_text(result.reply, parse_mode="Markdown")


def build_telegram_app(agent: SupportAgent) -> Application | None:
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram channel disabled")
        return None
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["agent"] = agent
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
