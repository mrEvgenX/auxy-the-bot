import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import User



logging.basicConfig(level=logging.INFO)
TELEGRAM_BOT_API_TOKEN = os.environ['TELEGRAM_BOT_API_TOKEN']
bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
dp = Dispatcher(bot)

orm_engine = create_async_engine(os.environ['DATABASE_URI'], echo=True)
OrmSession = sessionmaker(orm_engine, expire_on_commit=False, class_=AsyncSession)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    sender = message['from']
    chat = message['chat']
    dt = message['date']
    if chat['type'] == 'private':
        async with OrmSession() as session:
            user = await session.get(User, sender['id'])
            if not user:
                user = User(
                    id=sender['id'],
                    username=sender['username'],
                    first_name=sender['first_name'],
                    last_name=sender['last_name'],
                    lang=sender['language_code'],
                    joined=dt
                )
                session.add(user)
                await session.commit()
                await message.answer(f'Привет {user.first_name}, будем знакомы!')
            else:
                await message.answer(f'Привет {user.first_name}, очень приятно вас снова слышать!')
    else:
        await message.answer('Пожалуйста, пишите мне ЛС')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
