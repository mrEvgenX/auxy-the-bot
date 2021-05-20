import logging
import json
from aiogram import Bot, Dispatcher, executor, types
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .settings import TELEGRAM_BOT_API_TOKEN, DATABASE_URI, WHITELISTED_USERS
from .models import BotSettings, User
from .middleware import WhitelistMiddleware


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
dp = Dispatcher(bot)

orm_engine = create_async_engine(DATABASE_URI, echo=True)
OrmSession = sessionmaker(orm_engine, expire_on_commit=False, class_=AsyncSession)
end_of_workday_reminder_config = None


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='start')
async def start(message: types.Message):
    """
    Регистрация пользователя, приветствие, краткое руководство для начала работы
    """
    sender = message['from']
    dt = message['date']
    async with OrmSession() as session:
        user = await session.get(User, sender['id'])
        if not user:
            user = User(
                id=sender['id'],
                username=sender['username'],
                first_name=sender['first_name'],
                last_name=sender['last_name'],
                lang=sender['language_code'],
                joined_dt=dt
            )
            session.add(user)
            await session.commit()
            await message.answer(
                f'Привет {user.first_name}, будем знакомы! Я буду помогать'
            )
        else:
            await message.answer(
                f'Привет {user.first_name}, очень приятно вас снова слышать!\n'
                'Чтобы узнать более подробно, что я умею, наберите, пожалуйста, команду /help.'
            )


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='help')
async def help_(message: types.Message):
    """
    Подробное пользовательское руководство по использованию функций бота
    """
    await message.answer(
        'Меня назвали Окси, или Auxy по-английски. Это идет от слова auxilary - вспомогательный.\n'
        'Мое призвание - помогать поддерживать ваши дела в порядке.\n'
        'Сейчас я учусь напоминать об окончании рабочего дня и необходимости составить план на следующий день. '
        'В будущем, планируется много другого функционала, но об этом будет рассказано позже.'
    )


async def on_startup(_):
    global end_of_workday_reminder_config
    async with OrmSession() as session:
        end_of_workday_reminder_settings_obj = await session.get(BotSettings, 'end_of_workday_reminder')
        if end_of_workday_reminder_settings_obj:
            end_of_workday_reminder_config = end_of_workday_reminder_settings_obj.content
            logging.info(json.dumps(end_of_workday_reminder_config, indent=4, sort_keys=True))
        else:
            logging.error('Section "end_of_workday_reminder" is absent in db')
            exit(1)


if __name__ == '__main__':
    dp.middleware.setup(WhitelistMiddleware(WHITELISTED_USERS))
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
