from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from auxy.settings import TELEGRAM_BOT_API_TOKEN


bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
