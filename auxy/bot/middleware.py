import logging
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler


class WhitelistMiddleware(BaseMiddleware):
    
    def __init__(self, users_whitelist=None):
        super().__init__()
        self.users_whitelist = users_whitelist if users_whitelist else []

    async def on_pre_process_message(self, message: types.Message, data: dict):
        sender = message['from']
        if self.users_whitelist and sender['id'] not in self.users_whitelist:
            await message.answer(
                'Извините, но пока мой создатель не дает добро на общение с вами.\n'
                'Если что-то поменяется, я постараюсь вам это сообщить.'
            )
            logging.info(
                f'User {sender["first_name"]} (@{sender["username"]}) id={sender["id"]} '
                f'message: {message["text"]}'
            )
            raise CancelHandler()
