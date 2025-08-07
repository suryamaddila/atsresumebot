# ATS Resume Bot - Complete Deployment Guide

A Telegram bot that creates ATS-compliant resumes using AI optimization.

## Features

- 📄 **Resume Upload**: PDF, TXT, DOCX support
- 🤖 **AI Optimization**: OpenAI-powered resume enhancement
- 💳 **Payment Integration**: UPI payments with verification
- 📊 **ATS Scoring**: 98% compatibility targeting
- 📱 **User-Friendly**: Step-by-step guided process

## Quick Deployment on Render

### 1. Prepare Your Repository

```bash
# Clone or fork this repository
git clone <your-repo-url>
cd ats-resume-bot

# Complete project structure with your credentials configured for Render deployment

### Render Environment Variables Setup
```
```bash
TELEGRAM_BOT_TOKEN=8450693332:AAHS78W-NIvPomRihJH5Zd0RIzMYQmvs3co
OPENAI_API_KEY=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
CASHFREE_CLIENT_ID=cfsk_ma_prod_a941e4435990817c8f02c3b9325d7a67_729a32ec  
CASHFREE_APP_ID=493860aa4a9c632b73e541241d068394
CASHFREE_CLIENT_SECRET=YOUR_CASHFREE_CLIENT_SECRET_HERE
PAYMENT_AMOUNT=10
PAYMENT_GATEWAY_MODE=production
UPI_ID=suryaresume@paytm
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
BOT_USERNAME=suryaatsresumebot

```
