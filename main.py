import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.start_handler import start
from handlers.resume_handler import handle_resume
from handlers.jobdesc_handler import handle_job_description

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8450693332:AAHS78W-NIvPomRihJH5Zd0RIzMYQmvs3co"

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_resume))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_job_description))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
