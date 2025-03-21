import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from datetime import datetime

from config import TOKEN, DEBUG
from handlers import register_handlers
from inline_handler import register_inline_handler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)


# Параметры вебхука
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN', 'bcxbot.duckdns.org')
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

# Параметры веб-сервера
WEBAPP_HOST = '0.0.0.0'  # Слушать на всех интерфейсах
WEBAPP_PORT = 8443


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logger.info("Webhook удалён")


async def handle_update(request: web.Request):
    bot = request.app['bot']
    dispatcher = request.app['dispatcher']
    update = await request.json()
    await dispatcher.feed_raw_update(bot, update)
    return web.Response()


async def main():
    # Создание экземпляра бота и диспетчера
    session = AiohttpSession()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML.value), session=session)

    dp = Dispatcher()

    # Регистрация обработчиков
    register_handlers(dp)
    register_inline_handler(dp)

    if DEBUG:
        # Режим отладки: использовать long polling
        logger.info("🚀 Запуск в режиме DEBUG (Polling)")
        await dp.start_polling(bot)
    else:
        # Продакшн-режим: использовать webhook
        logger.info("🚀 Запуск в режиме PRODUCTION (Webhook)")

        # Создание веб-приложения aiohttp
        app = web.Application()
        app['bot'] = bot
        app['dispatcher'] = dp
        app.router.add_post(WEBHOOK_PATH, handle_update)

        # Настройка хуков на запуск и остановку
        app.on_startup.append(lambda _: on_startup(bot))
        app.on_shutdown.append(lambda _: on_shutdown(bot))

        # Запуск веб-сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()

        logger.info(f"Веб-сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")

        # Бесконечный цикл для поддержания работы
        try:
            while True:
                await asyncio.sleep(3600)  # Спать час
        except (KeyboardInterrupt, SystemExit):
            logger.info("Остановка бота...")

if __name__ == "__main__":
    asyncio.run(main())

"""
docker-compose run --rm certbot certonly --webroot \
  --webroot-path /var/www/certbot \
  --email office@afg.ge \
  --agree-tos \
  --no-eff-email \
  -d bcxbot.duckdns.org
  
"""