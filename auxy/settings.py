import os

WHITELISTED_USERS = list(map(int, os.environ['AUXY_WHITELISTED_USERS'].split(',')))
WHITELISTED_CHATS = list(map(int, os.environ['AUXY_WHITELISTED_CHATS'].split(',')))

TELEGRAM_BOT_API_TOKEN = os.environ['AUXY_TELEGRAM_BOT_API_TOKEN']

DATABASE_URI = os.environ['AUXY_DATABASE_URI']
