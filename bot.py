import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers.start import router as start_router
from handlers.trainer import router as trainer_router
from handlers.menu import router as menu_router
from handlers.legal_database import router as legal_database_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Include all routers
    dp.include_router(start_router)
    dp.include_router(trainer_router)
    dp.include_router(menu_router)
    dp.include_router(legal_database_router)  # Add legal database router

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())