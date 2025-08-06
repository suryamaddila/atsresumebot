import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from modules.resume_processor import analyze_and_generate_pdf
from modules.cashfree import verify_utr
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
user_states = {}
user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send your resume (PDF or DOCX) to begin.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    file = update.message.document
    if file.mime_type in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        file_path = f"temp/{user_id}_{file.file_name}"
        new_file = await file.get_file()
        await new_file.download_to_drive(file_path)
        user_files[user_id] = file_path
        user_states[user_id] = 'awaiting_jd'
        await update.message.reply_text("✅ Resume received. Now, send the job description.")
    else:
        await update.message.reply_text("❌ Please upload a valid PDF or DOCX resume.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == 'awaiting_jd':
        resume_path = user_files.get(user_id)
        jd = text
        output_path = f"temp/{user_id}_ats_resume.pdf"
        await analyze_and_generate_pdf(resume_path, jd, output_path)
        user_states[user_id] = 'awaiting_payment'
        user_files[user_id] = output_path
        await update.message.reply_text("💵 Please pay ₹5 via UPI and send the UTR number.")
    elif user_states.get(user_id) == 'awaiting_payment':
        if verify_utr(text):
            await update.message.reply_document(document=open(user_files[user_id], 'rb'))
            await update.message.reply_text("✅ Payment verified. Here is your optimized resume.")
            user_states[user_id] = None
            user_files[user_id] = None
        else:
            await update.message.reply_text("❌ Invalid UTR. Please try again.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
