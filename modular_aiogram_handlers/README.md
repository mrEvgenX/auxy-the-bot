# Modular aiogram handlers

`test_cmd.py`

```python
from modular_aiogram_handlers import Blueprint


test_cmd = Blueprint()


@test_cmd.message_handler(commands='hello')
async def process_hello_command(message):
    await message.answer('Hello!')

@test_cmd.message_handler(commands='bye')
async def process_hello_command(message):
    await message.answer('Bye!')

```

`main.py`

```python
from aiogram import Bot, Dispatcher, executor
from test_cmd import test_cmd


bot = Bot(token='TELEGRAM_BOT_API_TOKEN')
dp = Dispatcher(bot)
test_cmd.apply_registration(dp)
executor.start_polling(dp, skip_updates=True)
```
