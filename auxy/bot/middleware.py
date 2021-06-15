import logging
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware, LifetimeControllerMiddleware
from aiogram.dispatcher.handler import CancelHandler
from auxy.db.models import User, Chat
from auxy.db import OrmSession


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class WhitelistMiddleware(BaseMiddleware):

    def __init__(self, users_whitelist=None, chats_whitelist=None):
        super().__init__()
        self.users_whitelist = users_whitelist if users_whitelist else []
        self.chats_whitelist = chats_whitelist if chats_whitelist else []

    async def on_pre_process_message(self, message: types.Message, data: dict):
        from_user = types.User.get_current()
        sender_chat = types.Chat.get_current()
        if from_user.id not in self.users_whitelist:
            await message.answer(
                'Извините, но пока мой создатель не дает добро на общение с вами.\n'
                'Если что-то поменяется, я постараюсь вам это сообщить.'
            )
            logging.info(
                f'User {from_user.first_name} (@{from_user.username}) id={from_user.id} '
                f'message: {message.text}'
            )
            raise CancelHandler()
        if sender_chat.id not in self.chats_whitelist:
            await message.answer(
                'Извините, но пока мой создатель не дает добро на общение в данном чате.\n'
                'Если что-то поменяется, я постараюсь вам это сообщить.'
            )
            logging.info(
                f'Chat {sender_chat.first_name} (@{sender_chat.username}) id={sender_chat.id} '
                f'message: {message["text"]}'
            )
            raise CancelHandler()


class GetOrCreateUserMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ['error', 'update', 'channel_post', 'poll']

    async def pre_process(self, obj, data, *args):
        from_user = types.User.get_current()
        async with OrmSession() as session:
            # TODO take care about caching
            user = await session.get(User, from_user.id)
            data['user'] = user
            data['is_new_user'] = False
            if not data['user']:
                dt = obj.date
                log.info(f'Creating user @{from_user.username} with id {from_user.id}')
                user = User(
                    id=from_user.id,
                    username=from_user.username,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    lang=from_user.language_code,
                    joined_dt=dt
                )
                session.add(user)
                await session.commit()
                data['user'] = user
                data['is_new_user'] = True


class GetOrCreateChatMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ['error', 'update', 'inline_query', 'chosen_inline_result', 'callback_query'
                     'shipping_query', 'pre_checkout_query', 'poll', 'poll_answer']

    async def pre_process(self, obj, data, *args):
        if isinstance(obj, types.ChatMemberUpdated):
            sender_chat = types.ChatMemberUpdated.get_current().chat
        else:
            sender_chat = types.Chat.get_current()
        async with OrmSession() as session:
            # TODO take care about caching
            chat = await session.get(Chat, sender_chat.id)
            data['chat'] = chat
            data['is_new_chat'] = False
            if not data['chat']:
                dt = obj.date
                log.info(f'Creating chat @{sender_chat.username} with id {sender_chat.id}')
                chat = Chat(
                    id=sender_chat.id,
                    type=sender_chat.type,
                    username=sender_chat.username,
                    joined_dt=dt
                )
                session.add(chat)
                await session.commit()
                data['chat'] = chat
                data['is_new_chat'] = True
