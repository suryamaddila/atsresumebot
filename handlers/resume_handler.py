from telegram import Update
from telegram.ext import ContextTypes

async def handle_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("Please upload a valid PDF file.")
        return
    await update.message.reply_text("Resume received! Now, please send the job description.")
    context.user_data["resume_file_id"] = document.file_id
