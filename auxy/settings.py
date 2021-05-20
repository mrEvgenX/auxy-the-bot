import os

SUPERUSERS = list(map(int, os.environ['AUXY_SUPERUSERS'].split(',')))

WHITELISTED_USERS = list(map(int, os.environ['AUXY_WHITELISTED_USERS'].split(',')))

TELEGRAM_BOT_API_TOKEN = os.environ['AUXY_TELEGRAM_BOT_API_TOKEN']

DATABASE_URI = os.environ['AUXY_DATABASE_URI']
