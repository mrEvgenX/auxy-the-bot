import logging
from aiogram import types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from auxy.db import OrmSession
from auxy.db.models import User, TodoItemLogMessage
from modular_aiogram_handlers import Blueprint


class LogMessageForm(StatesGroup):
    todo_item_id = State()
    log_message_text = State()


item_logging = Blueprint()


@item_logging.message_handler(commands='log')
async def log_message_about_work(message: types.Message, user: User, state: FSMContext):
    dt = message.date
    async with OrmSession() as session:
        todo_list = await user.get_for_day(session, dt.date())
        items_num = len(todo_list.items) if todo_list else 0
        if items_num > 0:
            items_texts = [todo_item.text for todo_item in todo_list.items]
            await state.update_data(todo_items_num=items_num)
            await state.update_data(todo_items_texts=items_texts)
            await state.update_data(todo_items_ids=[todo_item.id for todo_item in todo_list.items])
            if items_num > 1:
                await LogMessageForm.todo_item_id.set()
                await message.reply(f'Напишите, пожалуйста, порядковый номер сегодняшней задачи от 1 до {items_num}')
            else:
                await state.update_data(todo_item_in_list_pos=0)
                await LogMessageForm.log_message_text.set()
                await message.reply(emojize(text(
                    text('В плане один единственный пункт:'),
                    text('    :pushpin:', items_texts[0]),
                    text('Напишите свое сообщение и я его сохраню'),
                    sep='\n')))
        else:
            await message.answer('Извините, записи можно вести пока только по сегодняшним планам, '
                                 'а у вас ничего не запланировано')


@item_logging.message_handler(lambda message: message.text.isdigit() and int(message.text) >= 1,
                              state=LogMessageForm.todo_item_id)
async def process_todo_item_id(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        items_num = data['todo_items_num']
        item_pos = int(message.text) - 1
        if item_pos >= items_num:
            await message.reply(f'В вашем сегодняшнем плане нет столько пунктов, апишите число от 1 до {items_num}')
        else:
            data['todo_item_in_list_pos'] = item_pos
            item_text = data['todo_items_texts'][item_pos]
            await LogMessageForm.next()
            await message.reply(emojize(text(
                text('Выбранный вами пункт:'),
                text('    :pushpin:', item_text),
                text('Теперь напишите само сообщение'),
                sep='\n')))


@item_logging.message_handler(lambda message: not message.text.isdigit() or int(message.text) < 1,
                    state=LogMessageForm.todo_item_id)
async def process_todo_item_id_invalid(message: types.Message):
    await message.reply('Мне нужна цифра больше единицы')


@item_logging.message_handler(state=LogMessageForm.log_message_text)
async def process_log_message_text(message: types.Message, state: FSMContext):
    dt = message.date
    async with state.proxy() as data:
        async with OrmSession() as session:
            item_in_list_pos = data['todo_item_in_list_pos']
            item_id = data['todo_items_ids'][item_in_list_pos]
            log_message = TodoItemLogMessage(
                todo_item_id=item_id,
                text=message.text,
                created_dt=dt
            )
            logging.info(log_message)
            session.add(log_message)
            await session.commit()
    await message.reply(emojize(text(
        text('Все, так и запишу:'),
        text('    :pencil2:', message.text),
        sep='\n')))
    await state.finish()
