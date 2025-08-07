import os
import sys
import logging
from config.settings import Config
from bot.handlers import ATSResumeBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to start the bot"""
    try:
        # Initialize configuration
        config = Config()
        
        # Validate required environment variables
        if not config.validate():
            logger.error("Configuration validation failed. Please check your environment variables.")
            sys.exit(1)
        
        # Initialize and start bot
        bot = ATSResumeBot(config)
        logger.info("Starting ATS Resume Bot...")
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()