import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import settings
from app.database.connection import init_db

# Barcha routerlarni import qiling
from app.handlers.user import user_router
# Masalan, boshqa handler fayllaringiz bo'lsa:
# from app.handlers.settings import settings_router
# from app.handlers.stats import stats_router

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Barcha routerlarni qo'shing
    dp.include_router(user_router)
    # dp.include_router(settings_router)
    # dp.include_router(stats_router)

    logging.info("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
