import logging
from sqlalchemy.future import select
from aiogram import types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from auxy.db import OrmSession
from auxy.db.models import User, Chat, Project, ItemNote
from auxy.utils import PeriodBucket
from modular_aiogram_handlers import Blueprint


class AddNoteToItemForm(StatesGroup):
    item_id = State()
    note_text = State()


item_logging = Blueprint()


@item_logging.message_handler(commands='log')
async def log_message_about_work(message: types.Message, user: User, chat: Chat, state: FSMContext):
    dt = message.date
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
            Project.owner_user_id == user.id,
            Project.chat_id == chat.id
        ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()

        bucket = PeriodBucket.new(project.period_bucket_mode, dt)
        items_list = await project.get_for_period(session, bucket)
        items_num = len(items_list.items) if items_list else 0
        if items_num > 0:
            items_texts = [item.text for item in items_list.items]
            await state.update_data(items_num=items_num)
            await state.update_data(items_texts=items_texts)
            await state.update_data(items_ids=[item.id for item in items_list.items])
            if items_num > 1:
                await AddNoteToItemForm.item_id.set()
                await message.reply(f'Напишите, пожалуйста, порядковый номер сегодняшней задачи от 1 до {items_num}')
            else:
                await state.update_data(item_in_list_pos=0)
                await AddNoteToItemForm.note_text.set()
                await message.reply(emojize(text(
                    text('В плане один единственный пункт:'),
                    text('    :pushpin:', items_texts[0]),
                    text('Напишите свое сообщение и я его сохраню'),
                    sep='\n')))
        else:
            await message.answer('Извините, записи можно вести пока только по сегодняшним планам, '
                                 'а у вас ничего не запланировано')


@item_logging.message_handler(lambda message: message.text.isdigit() and int(message.text) >= 1,
                              state=AddNoteToItemForm.item_id)
async def process_item_id(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        items_num = data['items_num']
        item_pos = int(message.text) - 1
        if item_pos >= items_num:
            await message.reply(f'В вашем сегодняшнем плане нет столько пунктов, напишите число от 1 до {items_num}')
        else:
            data['item_in_list_pos'] = item_pos
            item_text = data['items_texts'][item_pos]
            await AddNoteToItemForm.next()
            await message.reply(emojize(text(
                text('Выбранный вами пункт:'),
                text('    :pushpin:', item_text),
                text('Теперь напишите само сообщение'),
                sep='\n')))


@item_logging.message_handler(lambda message: not message.text.isdigit() or int(message.text) < 1,
                              state=AddNoteToItemForm.item_id)
async def process_item_id_invalid(message: types.Message):
    await message.reply('Мне нужна цифра больше единицы')


@item_logging.message_handler(state=AddNoteToItemForm.note_text)
async def process_note_text(message: types.Message, user: User, chat: Chat, state: FSMContext):
    dt = message.date
    async with state.proxy() as data:
        async with OrmSession() as session:
            select_stmt = select(Project)\
                .where(
                    Project.chat_id == chat.id
                )\
                .order_by(Project.id)
            projects_result = await session.execute(select_stmt)
            project = projects_result.scalars().first()

            item_in_list_pos = data['item_in_list_pos']
            item_id = data['items_ids'][item_in_list_pos]
            log_message = ItemNote(
                project_id=project.id,
                item_id=item_id,
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
