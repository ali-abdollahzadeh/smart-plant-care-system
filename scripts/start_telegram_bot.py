import logging
from telegram_bot import bot  # Import the initialized bot

# Configure logging
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        logging.info("Starting Telegram bot...")
        bot.polling()  # Start polling the Telegram bot for updates
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped by user.")
    finally:
        logging.info("Shutdown complete.")
