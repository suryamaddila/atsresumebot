import logging
import os
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.start_handler import start
from handlers.resume_handler import handle_resume
from handlers.jobdesc_handler import handle_job_description

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

def main():
    # Build the application
    app = Application.builder().token(BOT_TOKEN).build()

    # Register command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_resume))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_job_description))

    # Run the bot
    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
