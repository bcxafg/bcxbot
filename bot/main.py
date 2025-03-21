import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from config import TOKEN
from handlers import register_handlers
from inline_handler import register_inline_handler

# Configure logging (combining features from original code)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)

async def cleanup():
    """Clean up resources (from original code)"""
    logger.info("🧹 Starting cleanup...")
    #In aiogram, cleanup is handled automatically when the bot stops.  No explicit actions needed here.
    logger.info("Cleanup completed")

async def main():
    try:
        # Check for required token (from original code)
        if not TOKEN:
            logger.error("❌ No token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            return 1

        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
        dp = Dispatcher()

        # Register handlers (from edited code)
        register_handlers(dp)
        register_inline_handler(dp)

        # Start polling (from edited code, with error handling from original)
        logger.info("Starting bot...")
        try:
            await dp.start_polling(bot, allowed_updates=[
                "message",
                "callback_query",
                "inline_query"
            ])
            logger.info("✅ Bot polling started successfully")
        except Exception as e:
            logger.error(f"❌ Error in polling loop: {e}")
            return 1
        finally:
            logger.info("Exiting polling loop...")


    except Exception as e:
        logger.error(f"🔥 Fatal error: {str(e)}")
        if bot:
            await bot.close()  #Using bot.close() instead of app.stop() for aiogram
        return 1
    finally:
        logger.info("Cleaning up before exit...")
        await cleanup()
        logger.info("Cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())