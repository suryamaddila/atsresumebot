import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the ATS Resume Bot"""
    
    def __init__(self):
        # Telegram Configuration
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.BOT_USERNAME = os.getenv("BOT_USERNAME", "suryaatsresumebot")
        
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        # Cashfree Configuration
        self.CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID")
        self.CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID")
        self.CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET")
        self.PAYMENT_GATEWAY_MODE = os.getenv("PAYMENT_GATEWAY_MODE", "sandbox")  # sandbox or production
        
        # Database Configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        
        # Payment Configuration
        self.PAYMENT_AMOUNT = int(os.getenv("PAYMENT_AMOUNT", "5"))
        self.UPI_ID = os.getenv("UPI_ID", "suryaresume@paytm")
        
        # Environment Configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # File Upload Configuration
        self.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        self.ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.docx']
        
        # Rate Limiting
        self.RATE_LIMIT_MESSAGES = 10
        self.RATE_LIMIT_WINDOW = 60  # seconds
        
    def validate(self) -> bool:
        """Validate required configuration"""
        required_vars = [
            self.TELEGRAM_BOT_TOKEN,
            self.OPENAI_API_KEY,
            self.CASHFREE_CLIENT_ID,
            self.CASHFREE_APP_ID,
            self.CASHFREE_CLIENT_SECRET
        ]
        
        missing_vars = [var for var in required_vars if not var]
        
        if missing_vars:
            print(f"Missing required environment variables: {len(missing_vars)} variables")
            return False
            
        return True
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"