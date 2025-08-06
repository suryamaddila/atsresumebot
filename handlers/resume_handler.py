from telegram import Update
from telegram.ext import ContextTypes

async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Got your resume! Now please send the job description.")
