from telegram import Update
from telegram.ext import ContextTypes

async def handle_job_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_desc = update.message.text
    await update.message.reply_text("Thanks for the job description. Processing...")
    # You can add ATS processing logic here
    await update.message.reply_text("Job description processed successfully!")