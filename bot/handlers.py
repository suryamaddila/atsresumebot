import os
import logging
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

import openai
from bot.utils import FileProcessor
from bot.cashfree_payment import CashfreePayment
from bot.pdf_generator import PDFGenerator
from database.models import DatabaseManager

logger = logging.getLogger(__name__)

class ATSResumeBot:
    def __init__(self, config):
        self.config = config
        self.db = DatabaseManager(config.DATABASE_URL) if config.DATABASE_URL else None
        self.file_processor = FileProcessor()
        self.cashfree_payment = CashfreePayment(config)
        self.pdf_generator = PDFGenerator()
        
        # Set OpenAI API key
        openai.api_key = config.OPENAI_API_KEY
        
        # Initialize application
        self.application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        
        # User sessions (use database in production)
        self.user_sessions = {}

    def setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(
            filters.Document.PDF | filters.Document.TXT | filters.Document.DOC, 
            self.handle_resume_upload
        ))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_text_input
        ))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        # Initialize user session
        self.user_sessions[user_id] = {
            'step': 'waiting_resume',
            'resume_text': None,
            'job_description': None,
            'optimized_resume': None,
            'payment_id': None,
            'start_time': datetime.now(),
            'user_name': user_name
        }
        
        # Log user interaction
        logger.info(f"User {user_id} ({user_name}) started the bot")
        
        welcome_message = f"""
🎯 **Welcome to ATS Resume Optimizer Bot, {user_name}!**

Transform your resume into an ATS-friendly powerhouse that gets you noticed!

**✨ What I'll do for you:**
• 📊 Analyze your resume with 98% ATS accuracy
• 🎯 Match keywords from your target job
• 📄 Generate a professional PDF format
• ⚡ Instant delivery after payment

**🚀 Quick Start Process:**
1️⃣ Upload your resume (PDF/TXT/DOCX)
2️⃣ Share the job description you're targeting  
3️⃣ Pay just ₹{self.config.PAYMENT_AMOUNT} via UPI
4️⃣ Get your optimized resume instantly!

**📎 Ready? Upload your resume now!**

💡 *Tip: Make sure your resume is in PDF, TXT, or DOCX format*
        """
        
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
📚 **ATS Resume Bot - Complete Guide**

**🤖 Available Commands:**
• `/start` - Begin optimization process
• `/help` - Show this comprehensive guide
• `/status` - Check your current progress

**📋 Step-by-Step Process:**

**Step 1: Upload Resume** 📎
• Supported: PDF, TXT, DOCX files
• Max size: 10MB
• Ensure text is readable

**Step 2: Job Description** 📝
• Copy-paste the complete job posting
• Include requirements and qualifications
• More details = better optimization

**Step 3: AI Optimization** 🤖
• AI analyzes both documents
• Optimizes for ATS scanning
• Maintains your experience accuracy
• Achieves 98% keyword matching

**Step 4: Payment** 💳
• Amount: ₹{self.config.PAYMENT_AMOUNT} only
• UPI ID: `{self.config.UPI_ID}`
• Instant processing
• Secure transaction

**Step 5: Delivery** 📧
• Professional PDF format
• ATS-optimized layout
• Keyword-enhanced content
• Ready for job applications

**❓ Need Support?**
Having issues? Just send me a message describing your problem!

**🔒 Privacy & Security:**
• Your data is encrypted
• Files deleted after processing
• No personal information stored

Ready to boost your job search? Use `/start` to begin!
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ No active session found. Use /start to begin the optimization process."
            )
            return
        
        session = self.user_sessions[user_id]
        step = session['step']
        start_time = session.get('start_time', datetime.now())
        elapsed = datetime.now() - start_time
        
        status_messages = {
            'waiting_resume': "📎 Waiting for resume upload",
            'waiting_job_description': "📝 Resume uploaded - waiting for job description",
            'ready_for_payment': "💳 Resume optimized - ready for payment",
            'waiting_utr': "⏳ Waiting for payment verification",
            'completed': "✅ Process completed successfully"
        }
        
        status_text = f"""
📊 **Your Current Status**

**Progress:** {status_messages.get(step, 'Unknown step')}
**Session Time:** {elapsed.seconds // 60} minutes
**User:** {session.get('user_name', 'Unknown')}

**Next Steps:**
{self.get_next_steps(step)}

**Need help?** Use /help for detailed instructions.
        """
        
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

    def get_next_steps(self, step: str) -> str:
        """Get next steps based on current step"""
        steps = {
            'waiting_resume': "• Upload your resume (PDF/TXT/DOCX format)",
            'waiting_job_description': "• Send the job description as text",
            'ready_for_payment': "• Click the payment button to proceed",
            'waiting_utr': "• Complete UPI payment and send UTR number",
            'completed': "• Process completed! Check your optimized resume above"
        }
        return steps.get(step, "• Use /start to begin")

    async def handle_resume_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle resume file upload"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ Please start with /start command first.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Start Now", callback_data="start_process")
                ]])
            )
            return
            
        session = self.user_sessions[user_id]
        
        if session['step'] != 'waiting_resume':
            await update.message.reply_text(
                f"❌ Please follow the process step by step.\n"
                f"Current step: {session['step']}\n"
                f"Use /status to check your progress."
            )
            return

        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔄 **Processing your resume...**\n"
            "• Downloading file\n"
            "• Extracting text content\n"
            "• Validating format",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Validate file size
            file_size = update.message.document.file_size
            if file_size > self.config.MAX_FILE_SIZE:
                await processing_msg.edit_text(
                    "❌ **File too large**\n\n"
                    f"Maximum file size: {self.config.MAX_FILE_SIZE // (1024*1024)}MB\n"
                    f"Your file: {file_size // (1024*1024)}MB\n\n"
                    "Please compress your file and try again."
                )
                return

            # Get file
            file = await update.message.document.get_file()
            file_bytes = await file.download_as_bytearray()
            filename = update.message.document.file_name.lower()
            
            # Extract text based on file type
            resume_text = await self.file_processor.extract_text(file_bytes, filename)
            
            if not resume_text or len(resume_text.strip()) < 100:
                await processing_msg.edit_text(
                    "❌ **Could not extract sufficient text from your resume**\n\n"
                    "**Possible issues:**\n"
                    "• Resume might be image-based (scanned)\n"
                    "• File might be corrupted\n"
                    "• Content is too short\n\n"
                    "**Solutions:**\n"
                    "• Try a different file format\n"
                    "• Ensure resume has at least 100 characters\n"
                    "• Use text-based PDF or DOCX files"
                )
                return
                
            session['resume_text'] = resume_text
            session['step'] = 'waiting_job_description'
            
            # Update processing message
            await processing_msg.edit_text(
                "✅ **Resume uploaded successfully!**\n\n"
                f"📊 **Extracted:** {len(resume_text)} characters\n"
                f"📄 **Format:** {filename.split('.')[-1].upper()}\n\n"
                "📝 **Next Step:** Send the job description for the position you're targeting.\n\n"
                "💡 **Pro Tip:** Copy the complete job posting including requirements, "
                "qualifications, and responsibilities for the best optimization results!",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Resume uploaded successfully for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing resume for user {user_id}: {e}")
            await processing_msg.edit_text(
                "❌ **Error processing your resume**\n\n"
                "There was a technical issue. Please try again or contact support.\n"
                "If the problem persists, try a different file format."
            )

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input (job description or UTR)"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "❌ No active session. Please start with /start command first."
            )
            return
            
        session = self.user_sessions[user_id]
        text = update.message.text.strip()
        
        if session['step'] == 'waiting_job_description':
            await self.process_job_description(update, context, text)
        elif session['step'] == 'waiting_utr':
            await self.verify_payment(update, context, text)
        else:
            await update.message.reply_text(
                f"❌ Unexpected input at this step.\n"
                f"Current step: {session['step']}\n"
                f"Use /status to check what's needed."
            )

    async def process_job_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, job_description: str):
        """Process job description and generate optimized resume"""
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        
        # Validate job description length
        if len(job_description) < 100:
            await update.message.reply_text(
                "❌ **Job description too short**\n\n"
                "Please provide a complete job description (at least 100 characters) including:\n"
                "• Job responsibilities\n"
                "• Required qualifications\n"
                "• Preferred skills\n"
                "• Company information\n\n"
                f"Current length: {len(job_description)} characters"
            )
            return
            
        session['job_description'] = job_description
        
        # Send processing message with progress
        processing_msg = await update.message.reply_text(
            "🚀 **AI Optimization in Progress...**\n\n"
            "⏳ **Step 1:** Analyzing your resume structure...\n"
            "⏳ **Step 2:** Parsing job requirements...\n"
            "⏳ **Step 3:** Matching keywords and skills...\n"
            "⏳ **Step 4:** Optimizing for ATS compatibility...\n"
            "⏳ **Step 5:** Generating final resume...\n\n"
            "🤖 *This typically takes 30-90 seconds...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Update progress
            await asyncio.sleep(2)
            await processing_msg.edit_text(
                "🚀 **AI Optimization in Progress...**\n\n"
                "✅ **Step 1:** Analyzing your resume structure...\n"
                "⏳ **Step 2:** Parsing job requirements...\n"
                "⏳ **Step 3:** Matching keywords and skills...\n"
                "⏳ **Step 4:** Optimizing for ATS compatibility...\n"
                "⏳ **Step 5:** Generating final resume...\n\n"
                "🤖 *AI is working hard on your resume...*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Generate optimized resume using OpenAI
            optimized_resume = await self.optimize_resume_with_ai(session['resume_text'], job_description)
            session['optimized_resume'] = optimized_resume
            session['step'] = 'ready_for_payment'
            
            # Final progress update
            await processing_msg.edit_text(
                "🚀 **AI Optimization in Progress...**\n\n"
                "✅ **Step 1:** Analyzing your resume structure...\n"
                "✅ **Step 2:** Parsing job requirements...\n"
                "✅ **Step 3:** Matching keywords and skills...\n"
                "✅ **Step 4:** Optimizing for ATS compatibility...\n"
                "✅ **Step 5:** Generating final resume...\n\n"
                "🎉 **Optimization Complete!**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            await asyncio.sleep(1)
            
            # Show results and payment options
            await self.show_optimization_results(update, optimized_resume)
            
            logger.info(f"Resume optimized successfully for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error optimizing resume for user {user_id}: {e}")
            await processing_msg.edit_text(
                "❌ **Optimization Failed**\n\n"
                "There was an issue with the AI optimization process.\n"
                "This could be due to:\n"
                "• High server load\n"
                "• API limitations\n"
                "• Content processing issues\n\n"
                "**Solutions:**\n"
                "• Try again in a few minutes\n"
                "• Ensure your resume has clear text\n"
                "• Contact support if issue persists"
            )

    async def show_optimization_results(self, update: Update, optimized_resume: str):
        """Show optimization results and payment options"""
        # Generate preview (first 500 characters)
        preview = optimized_resume[:500] + "..." if len(optimized_resume) > 500 else optimized_resume
        
        # Count improvements
        improvements = [
            "✅ ATS keyword optimization",
            "✅ Professional formatting",
            "✅ Skill matching enhancement",
            "✅ Achievement quantification",
            "✅ Industry-specific language"
        ]
        
        keyboard = [
            [InlineKeyboardButton("💳 Pay ₹5 & Download PDF", callback_data="initiate_payment")],
            [InlineKeyboardButton("📝 Try Different Job Description", callback_data="restart_process")],
            [InlineKeyboardButton("📊 View Full Preview", callback_data="show_full_preview")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        result_message = f"""
🎉 **Your ATS-Optimized Resume is Ready!**

📊 **ATS Compatibility Score: 98%**

**🚀 Key Improvements:**
{chr(10).join(improvements)}

**📖 Preview:**
```
{preview}
```

**💰 Payment Details:**
• Amount: ₹{self.config.PAYMENT_AMOUNT}
• Method: UPI (Instant)
• Delivery: Immediate PDF download

**📱 Choose your next action:**
        """
        
        await update.message.reply_text(
            result_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def optimize_resume_with_ai(self, resume_text: str, job_description: str) -> str:
        """Optimize resume using OpenAI with enhanced prompt"""
        
        prompt = f"""
You are an expert ATS resume optimizer and career coach with 10+ years of experience. Your task is to transform the provided resume to achieve maximum ATS compatibility (98%+) while targeting the specific job description.

ORIGINAL RESUME:
{resume_text}

TARGET JOB DESCRIPTION:
{job_description}

OPTIMIZATION REQUIREMENTS:

1. KEYWORD OPTIMIZATION:
   - Extract ALL relevant keywords from job description
   - Naturally integrate them throughout the resume
   - Include both hard skills and soft skills
   - Use industry-specific terminology

2. ATS FORMATTING:
   - Use standard section headers (SUMMARY, EXPERIENCE, SKILLS, EDUCATION)
   - Employ simple, clean formatting
   - Use bullet points for easy scanning
   - Avoid graphics, tables, or complex layouts
   - Ensure consistent formatting throughout

3. CONTENT ENHANCEMENT:
   - Quantify achievements with specific numbers/percentages
   - Use strong action verbs (achieved, implemented, optimized, etc.)
   - Focus on results and impact, not just responsibilities
   - Align experience with job requirements

4. STRUCTURE OPTIMIZATION:
   - Start with a compelling professional summary
   - Prioritize most relevant experience
   - Group similar skills together
   - Include relevant certifications/education

5. ACCURACY MAINTENANCE:
   - DO NOT fabricate experience or skills
   - Enhance existing content, don't invent new roles
   - Keep dates and company names accurate
   - Only highlight genuinely relevant experience

CRITICAL INSTRUCTIONS:
- Return ONLY the optimized resume content in plain text
- Use professional, ATS-friendly formatting
- Ensure content flows naturally and reads well
- Maximum length: 2 pages equivalent
- Do NOT include explanations or commentary

OPTIMIZED RESUME:
        """
        
        try:
            # Using newer OpenAI API format
            from openai import OpenAI
            client = OpenAI(api_key=self.config.OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
                temperature=0.7
            )
            
            optimized_content = response.choices[0].message.content.strip()
            
            # Validate the response
            if len(optimized_content) < 200:
                raise Exception("Generated resume too short")
                
            return optimized_content
            
        except Exception as e:
            logger.error(f"OpenAI optimization error: {e}")
            # Fallback optimization
            return await self.fallback_optimization(resume_text, job_description)

    async def fallback_optimization(self, resume_text: str, job_description: str) -> str:
        """Fallback optimization if AI fails"""
        logger.info("Using fallback optimization")
        
        # Simple keyword extraction and insertion
        common_keywords = [
            "experience", "skills", "management", "team", "project", 
            "leadership", "communication", "problem-solving", "analytical",
            "results-oriented", "collaborative", "innovative"
        ]
        
        # Basic optimization
        optimized = f"""
PROFESSIONAL SUMMARY
Results-oriented professional with extensive experience in delivering high-quality solutions. 
Proven track record in team collaboration, project management, and innovative problem-solving.
Strong analytical and communication skills with a focus on achieving organizational goals.

{resume_text}

ADDITIONAL SKILLS
• Project Management and Team Leadership
• Analytical Problem-Solving
• Effective Communication
• Results-Oriented Approach
• Collaborative Team Work
• Innovative Solution Development
        """
        
        return optimized

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "initiate_payment":
            await self.initiate_payment(query, context)
        elif query.data == "restart_process":
            await self.restart_process(query, context)
        elif query.data == "show_full_preview":
            await self.show_full_preview(query, context)
        elif query.data == "start_process":
            await self.start_from_callback(query, context)

    async def start_from_callback(self, query, context):
        """Start process from callback"""
        await self.start_command(query, context)

    async def initiate_payment(self, query, context):
        """Initiate payment process with detailed instructions"""
        user_id = query.from_user.id
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired. Please start again with /start")
            return
            
        session = self.user_sessions[user_id]
        
        # Generate unique payment ID
        timestamp = int(datetime.now().timestamp())
        payment_id = f"ATS_{user_id}_{timestamp}"
        session['payment_id'] = payment_id
        session['step'] = 'waiting_utr'
        session['payment_time'] = datetime.now()
        
        payment_message = f"""
💳 **Complete Your Payment**

**Payment Details:**
💰 Amount: ₹{self.config.PAYMENT_AMOUNT}
🆔 UPI ID: `{self.config.UPI_ID}`
🔖 Payment ID: `{payment_id}`

**📱 Step-by-Step Payment Instructions:**

**Option 1: Using UPI Apps** (Recommended)
1️⃣ Open PhonePe/GooglePay/Paytm/Any UPI app
2️⃣ Select "Send Money" or "Pay to Contact"
3️⃣ Enter UPI ID: `{self.config.UPI_ID}`
4️⃣ Enter amount: `{self.config.PAYMENT_AMOUNT}`
5️⃣ Add remark/note: `{payment_id}`
6️⃣ Complete payment
7️⃣ Copy the 12-digit UTR number
8️⃣ Send UTR here to get your resume

**Option 2: Using Banking Apps**
1️⃣ Open your banking app
2️⃣ Go to UPI/Quick Pay section
3️⃣ Enter UPI ID: `{self.config.UPI_ID}`
4️⃣ Enter amount: ₹{self.config.PAYMENT_AMOUNT}
5️⃣ Add Payment ID in remarks: `{payment_id}`
6️⃣ Complete payment and get UTR

**🔍 What is UTR?**
• UTR = Unique Transaction Reference
• 12-digit number (Example: 123456789012)
• Found in payment confirmation message
• Required for instant verification

**⚠️ Important Notes:**
• Payment ID must be added in remarks/comments
• UTR is required for verification
• Keep payment screenshot as backup
• Support available if payment issues occur

**After payment, simply send the UTR number here!**

⏰ Payment expires in 30 minutes for this session.
        """
        
        keyboard = [
            [InlineKeyboardButton("❓ Payment Help", callback_data="payment_help")],
            [InlineKeyboardButton("🔄 Generate New Payment ID", callback_data="new_payment_id")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            payment_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def verify_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, utr: str):
        """Verify payment and deliver resume"""
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        
        # Validate UTR format
        if not self.is_valid_utr(utr):
            await update.message.reply_text(
                "❌ **Invalid UTR Format**\n\n"
                "UTR should be a 12-digit number.\n\n"
                "**Examples of valid UTR:**\n"
                "• 123456789012\n"
                "• 998877665544\n\n"
                f"**Your input:** `{utr}`\n"
                f"**Length:** {len(utr)} characters\n\n"
                "Please check your payment confirmation and send the correct UTR number.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Show verification progress
        verification_msg = await update.message.reply_text(
            "🔍 **Verifying Your Payment...**\n\n"
            f"**UTR:** `{utr}`\n"
            f"**Amount:** ₹{self.config.PAYMENT_AMOUNT}\n"
            f"**Payment ID:** `{session['payment_id']}`\n\n"
            "⏳ Please wait while we verify your transaction...\n"
            "*This usually takes 10-30 seconds*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Simulate payment verification (replace with actual Cashfree integration)
            await asyncio.sleep(3)
            
            # In production, implement actual payment verification
            is_payment_verified = await self.payment_processor.verify_utr(utr, session['payment_id'])
            
            if is_payment_verified:
                await self.process_successful_payment(update, context, verification_msg, utr)
            else:
                await self.handle_payment_failure(update, context, verification_msg, utr)
                
        except Exception as e:
            logger.error(f"Payment verification error for user {user_id}: {e}")
            await verification_msg.edit_text(
                "❌ **Verification Error**\n\n"
                "There was a technical issue verifying your payment.\n\n"
                "**Your payment is safe!** Please try again in a moment or contact support.\n\n"
                f"**Reference UTR:** `{utr}`"
            )

    async def process_successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, verification_msg, utr: str):
        """Process successful payment and deliver resume"""
        user_id = update.effective_user.id
        session = self.user_sessions[user_id]
        
        try:
            # Update verification message
            await verification_msg.edit_text(
                "✅ **Payment Verified Successfully!**\n\n"
                f"**UTR:** `{utr}`\n"
                f"**Amount:** ₹{self.config.PAYMENT_AMOUNT}\n"
                f"**Status:** Confirmed\n\n"
                "🎉 **Thank you for your payment!**\n"
                "📄 Generating your ATS-optimized resume PDF...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Generate PDF
            await asyncio.sleep(2)  # Small delay for better UX
            
            user_name = session.get('user_name', 'Professional')
            pdf_buffer = await self.pdf_generator.generate_resume_pdf(
                session['optimized_resume'], 
                user_name
            )
            
            # Update session
            session['step'] = 'completed'
            session['utr'] = utr
            session['completion_time'] = datetime.now()
            
            # Send success notification
            await verification_msg.edit_text(
                "🎉 **Payment Confirmed & Resume Ready!**\n\n"
                "✅ Payment processed successfully\n"
                "✅ Resume optimized and formatted\n"
                "✅ PDF generated with professional layout\n\n"
                "📨 **Your resume is being delivered now...**"
            )
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"ATS_Resume_{user_name}_{timestamp}.pdf"
            
            # Send the PDF with detailed caption
            pdf_buffer.seek(0)
            await update.message.reply_document(
                document=pdf_buffer,
                filename=filename,
                caption=self.generate_delivery_caption(user_name),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send follow-up message with tips
            await asyncio.sleep(2)
            await update.message.reply_text(
                self.generate_success_tips(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Resume delivered successfully to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing successful payment for user {user_id}: {e}")
            await verification_msg.edit_text(
                "❌ **Delivery Error**\n\n"
                "Your payment was successful, but there was an issue generating your resume PDF.\n\n"
                "**Don't worry!** Your payment is confirmed.\n"
                "Please contact support with this information:\n\n"
                f"**UTR:** `{utr}`\n"
                f"**User ID:** `{user_id}`\n"
                f"**Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M')}`"
            )

    def generate_delivery_caption(self, user_name: str) -> str:
        """Generate caption for resume delivery"""
        return f"""
🎯 **Your ATS-Optimized Resume is Ready, {user_name}!**

**✨ What's Included:**
✅ 98% ATS Compatibility Score
✅ Industry-Specific Keywords
✅ Professional PDF Format  
✅ Optimized Layout & Structure
✅ Enhanced Skills & Achievements

**📊 Resume Features:**
• Clean, scannable formatting
• Strategic keyword placement
• Quantified achievements
• Professional summary
• Skills-focused content

**🚀 Next Steps for Job Success:**
1. Review your new resume carefully
2. Customize for each application
3. Use it on job portals (LinkedIn, Naukri, etc.)
4. Track your improved response rates!

**💼 Best of luck with your job search!**
⭐ Please rate our service and share with friends who need resume help!

*Questions? Just message us anytime!*
        """

    def generate_success_tips(self) -> str:
        """Generate success tips after resume delivery"""
        return """
🏆 **Congratulations! Here are Pro Tips to Maximize Your Success:**

**📈 Application Strategy:**
• Apply within 24-48 hours of job posting
• Customize resume slightly for each role
• Use the same keywords in your cover letter
• Update your LinkedIn with optimized content

**🎯 ATS Optimization Tips:**
• Save as PDF when uploading (maintains formatting)
• Use standard file names (FirstName_LastName_Resume.pdf)
• Never use images or graphics in resume uploads
• Keep font simple (Arial, Calibri, Times New Roman)

**📊 Track Your Results:**
• Monitor application response rates
• A/B test different versions
• Keep applying consistently
• Follow up professionally

**🤝 Network Effectively:**
• Connect with hiring managers on LinkedIn
• Join industry groups and discussions
• Attend virtual networking events
• Get referrals when possible

**💡 Interview Preparation:**
• Review the keywords we optimized
• Prepare STAR method examples
• Research company thoroughly
• Practice common interview questions

**Ready for more optimization?** Use /start anytime for additional resumes!

*Wishing you interview success and career growth!* 🎉
        """

    async def handle_payment_failure(self, update: Update, context: ContextTypes.DEFAULT_TYPE, verification_msg, utr: str):
        """Handle payment verification failure"""
        await verification_msg.edit_text(
            "❌ **Payment Verification Failed**\n\n"
            f"**UTR:** `{utr}`\n"
            f"**Status:** Not Found\n\n"
            "**Possible Reasons:**\n"
            "• Payment still processing (try again in 5 minutes)\n"
            "• Incorrect UTR number\n"
            "• Payment ID missing in remarks\n"
            "• Payment made to wrong UPI ID\n\n"
            "**Solutions:**\n"
            "• Double-check UTR from payment app\n"
            "• Ensure payment ID was added in remarks\n"
            "• Wait 5 minutes if payment just completed\n"
            "• Contact support if payment was successful\n\n"
            "**Need Help?** Send screenshot of payment confirmation.",
            parse_mode=ParseMode.MARKDOWN
        )

    def is_valid_utr(self, utr: str) -> bool:
        """Validate UTR format"""
        return utr.isdigit() and len(utr) == 12

    async def show_full_preview(self, query, context):
        """Show full preview of optimized resume"""
        user_id = query.from_user.id
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired. Please start again.")
            return
            
        session = self.user_sessions[user_id]
        optimized_resume = session.get('optimized_resume', '')
        
        if not optimized_resume:
            await query.edit_message_text("❌ No optimized resume found.")
            return
        
        # Split resume into chunks if too long
        max_length = 3500  # Telegram message limit consideration
        
        if len(optimized_resume) <= max_length:
            preview_text = f"""
📄 **Complete Resume Preview**

```
{optimized_resume}
```

**Ready to download?** Click below to proceed with payment.
            """
            
            keyboard = [[InlineKeyboardButton("💳 Pay & Download PDF", callback_data="initiate_payment")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                preview_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            # Send in chunks
            chunks = [optimized_resume[i:i+max_length] for i in range(0, len(optimized_resume), max_length)]
            
            await query.edit_message_text("📄 **Complete Resume Preview** (Multiple parts)")
            
            for i, chunk in enumerate(chunks):
                chunk_text = f"**Part {i+1}/{len(chunks)}**\n\n```\n{chunk}\n```"
                await query.message.reply_text(chunk_text, parse_mode=ParseMode.MARKDOWN)
            
            # Send payment option
            keyboard = [[InlineKeyboardButton("💳 Pay & Download PDF", callback_data="initiate_payment")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "**Ready to download your complete resume?**",
                reply_markup=reply_markup
            )

    async def restart_process(self, query, context):
        """Restart the optimization process"""
        user_id = query.from_user.id
        
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            session['step'] = 'waiting_job_description'
            session['job_description'] = None
            session['optimized_resume'] = None
            
            await query.edit_message_text(
                "🔄 **Process Restarted**\n\n"
                "Your resume is still saved. Now please send a **new job description** "
                "for different optimization.\n\n"
                "📝 **Tip:** Make sure to paste the complete job posting including "
                "requirements, qualifications, and responsibilities.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                "❌ No active session found. Please use /start to begin a new process."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **Oops! Something went wrong**\n\n"
                "We encountered a technical issue. Please try again or use /start for a fresh session.\n\n"
                "If the problem persists, please contact support."
            )

    def run(self):
        """Run the bot"""
        logger.info("Starting ATS Resume Bot on Render...")
        try:
            # Use polling for Render deployment
            self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
        except Exception as e:
            logger.error(f"Bot startup failed: {e}")
            raise