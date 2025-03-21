import os
import logging
import signal
import sys
import asyncio
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, InlineQueryHandler
from config import TOKEN, DEBUG, WEBHOOK_URL
from handlers import (
    start_command, help_command, currency_command, rico_command,
    error_handler, math_command, groupid_command
)
from inline_handler import inline_query
from logger import logger

app = None


def signal_handler(signum, frame):
    logger.info(f"🛑 Received signal {signum}, initiating shutdown...")
    if app and app.is_running:
        asyncio.create_task(cleanup())


async def cleanup():
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
    global app

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not TOKEN:
        logger.error("❌ No token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
        return 1

    app = ApplicationBuilder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    for curr in ["EUR", "USD", "AED", "PLN", "RUB"]:
        app.add_handler(CommandHandler(
            curr.lower(),
            lambda update, context, currency=curr: currency_command(update, context, currency)
        ))

    app.add_handler(CommandHandler("rico", rico_command))
    app.add_handler(CommandHandler("groupid", groupid_command))

    # Math expression handler
    app.add_handler(MessageHandler(
        filters.COMMAND & filters.Regex(r'^/[1-9]'),
        math_command
    ))

    # Inline handler
    app.add_handler(InlineQueryHandler(inline_query))

    await app.initialize()
    await app.start()

    if DEBUG:
        logger.info("🚀 Starting bot in DEBUG (polling) mode")
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "inline_query"],
            read_timeout=30,
            write_timeout=30
        )
    else:
        logger.info("🚀 Starting bot in PRODUCTION (webhook) mode")
        await app.bot.set_webhook(url=WEBHOOK_URL)
        await app.run_webhook(
            listen='127.0.0.1',
            port=8443,
            url_path=TOKEN,
            webhook_url=WEBHOOK_URL
        )

    try:
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"❌ Error: {e}")

    finally:
        await cleanup()


if __name__ == '__main__':
    asyncio.run(main())
