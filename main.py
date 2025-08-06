import os
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CommandHandler,
)
from handlers.start_handler import start
from handlers.resume_handler import handle_resume

BOT_TOKEN = os.getenv("BOT_TOKEN")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command: /start
    app.add_handler(CommandHandler("start", start))

    # Resume PDF or DOCX file handler
    app.add_handler(MessageHandler(filters.Document.ALL, handle_resume))

    # Run the bot
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
