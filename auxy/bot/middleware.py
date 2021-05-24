import asyncio
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from auxy.settings import SUPERUSERS


class WhitelistMiddleware(BaseMiddleware):
    
    def __init__(self, users_whitelist=None):
        super().__init__()
        self.users_whitelist = users_whitelist if not users_whitelist else []

    async def on_pre_process_message(self, message: types.Message, data: dict):
        sender = message['from']
        bot = self.manager.bot
        if self.users_whitelist and sender['id'] not in self.users_whitelist:
            await message.answer(
                'Извините, но пока мой создатель не дает добро на общение с вами.\n'
                'Если что-то поменяется, я постараюсь вам это сообщить.'
            )
            for superuser_id in SUPERUSERS:
                await bot.send_message(
                    superuser_id,
                    f'Пользователь {sender["first_name"]} под ником @{sender["username"]} с id={sender["id"]}'
                    f'отправил мне следующее сообщение:\n{message["text"]}'
                )
                await asyncio.sleep(.05)
            raise CancelHandler()
