"""
AI Post Check-in Bot - Main Entry Point
"""
import logging
import os
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
from handlers.checkin_handler import (
    start,
    handle_message,
    confirm_data,
    edit_field,
    handle_edit_input,
    cancel,
    CONFIRMING,
    EDITING,
)
from handlers.history_handler import show_history
from handlers.help_handler import show_help

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env file")

    app = Application.builder().token(token).build()

    # Main conversation flow
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler((filters.TEXT | filters.VOICE | filters.AUDIO) & ~filters.COMMAND, handle_message)],
        states={
            CONFIRMING: [CallbackQueryHandler(confirm_data)],
            EDITING: [
                CallbackQueryHandler(edit_field),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(conv_handler)

    logger.info("🤖 Post Check-in Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
