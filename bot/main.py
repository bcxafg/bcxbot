import os
import logging
import signal
import sys
import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, InlineQueryHandler
from config import TOKEN
from handlers import (
    start_command, help_command, currency_command, rico_command,
    error_handler, math_command, is_math_expression, groupid_command
)
from inline_handler import inline_query
from logger import logger

# Global variable for the bot application
app = None

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"🛑 Received signal {signum}, initiating shutdown...")
    if app and app.is_running:
        logger.info("Stopping bot application due to signal...")
        asyncio.create_task(cleanup())

async def cleanup():
    """Clean up resources"""
    global app
    logger.info("🧹 Starting cleanup...")

    if app:
        try:
            logger.info("🛑 Stopping bot application...")
            await app.stop()
            await app.shutdown()
            logger.info("✅ Bot application stopped")
        except Exception as e:
            logger.error(f"⚠️ Error stopping bot: {e}")

async def main():
    """Start the bot with polling."""
    global app

    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Check for required token
        if not TOKEN:
            logger.error("❌ No token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            return 1

        # Delete any existing webhook first
        logger.info("🔄 Removing any existing webhooks...")
        bot = Bot(token=TOKEN)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Existing webhook deleted")

        # Initialize bot with inline mode enabled
        logger.info("🚀 Initializing bot...")
        app = (ApplicationBuilder()
               .token(TOKEN)
               .build())

        # Add command handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))

        # Add currency command handlers using the updated currency_command function
        for curr in ["EUR", "USD", "AED", "PLN", "RUB"]:
            app.add_handler(CommandHandler(
                curr.lower(),
                lambda update, context, currency=curr: currency_command(update, context, currency)
            ))

        # Add Rico command handler
        app.add_handler(CommandHandler("rico", rico_command))

        # Add groupid command handler
        logger.info("Registering groupid command handler")
        app.add_handler(CommandHandler("groupid", groupid_command))

        # Add handler for mathematical expressions
        app.add_handler(MessageHandler(
            filters.COMMAND & filters.Regex(r'^/[1-9]'),
            math_command
        ))

        # Add inline query handler
        app.add_handler(InlineQueryHandler(inline_query))


        # Initialize and start bot
        await app.initialize()
        await app.start()
        logger.info("✅ Bot initialized and started")

        try:
            # Start polling with improved error handling
            await app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "inline_query"],
                read_timeout=30,
                write_timeout=30
            )
            logger.info("✅ Bot polling started successfully")

            # Keep the bot running
            logger.info("Bot is now running... Press Ctrl+C to stop")
            while True:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error in polling loop: {e}")
            return 1
        finally:
            logger.info("Exiting polling loop...")

    except Exception as e:
        logger.error(f"🔥 Fatal error: {str(e)}")
        if app:
            await app.stop()
        return 1
    finally:
        logger.info("Cleaning up before exit...")
        await cleanup()
        logger.info("Cleanup completed")

if __name__ == '__main__':
    asyncio.run(main())