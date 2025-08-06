from telegram import Update
from telegram.ext import ContextTypes

async def handle_job_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_desc = update.message.text
    context.user_data["job_description"] = job_desc

    await update.message.reply_text(
        "✅ Job description received!\n\nNow processing your optimized ATS resume..."
    )
    # TODO: Add PDF generation + UPI logic here
