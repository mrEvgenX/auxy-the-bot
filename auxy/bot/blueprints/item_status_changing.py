import re
from sqlalchemy.future import select
from aiogram import types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from auxy.db import OrmSession
from auxy.db.models import User, Chat, Project, Item
from auxy.utils import PeriodBucket, ItemStatus
from modular_aiogram_handlers import Blueprint


human_item_status = {
    ItemStatus.active: '',
    ItemStatus.done: 'Отмечу задачу как сделанную',
    ItemStatus.rejected: 'Понятно, эту задачу делать не будем',
}


class ChangeItemStatusForm(StatesGroup):
    item_id = State()


item_status_changing = Blueprint()


@item_status_changing.message_handler(commands=['done', 'reject'])
async def log_message_about_work(message: types.Message, user: User, chat: Chat, state: FSMContext):
    dt = message.date
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
                Project.chat_id == chat.id
            ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()

        bucket = PeriodBucket.new(project.period_bucket_mode, dt)
        items_list = await project.get_for_period(session, bucket)
        items_num = len(items_list.items) if items_list else 0
        if items_num > 0:
            items_texts = [item.text for item in sorted(items_list.items, key=lambda i: i.id)]
            item_new_status = message.get_command(pure=True)
            await state.update_data(item_new_status=item_new_status)
            await state.update_data(items_num=items_num)
            await state.update_data(items_texts=items_texts)
            await state.update_data(items_ids=[item.id for item in sorted(items_list.items, key=lambda i: i.id)])
            if items_num > 1:
                await ChangeItemStatusForm.item_id.set()
                keyboard = [
                    [types.KeyboardButton(f'{i+1}. {txt if len(txt) < 32 else txt[:29] + "..."}')]
                    for i, txt in enumerate(items_texts)
                ]
                await message.reply(
                    'Выберите, пожалуйста, задачу из списка '
                    f'текущего периода по порядковому номеру от 1 до {items_num}',
                    reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard)
                )
            else:
                items_list.items[0].status = ItemStatus[item_new_status]
                await session.commit()
                await message.reply(emojize(text(
                    text('В плане один единственный пункт:'),
                    text('    :pushpin:', items_texts[0]),
                    text(human_item_status[items_list.items[0].status]),
                    sep='\n')))
        else:
            await message.answer('Извините, у вас ничего не запланировано в ближайшее время')


@item_status_changing.message_handler(state=ChangeItemStatusForm.item_id)
async def process_item_id(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        mo = re.match(r'(\d+)(?:\. )?(.*)', message.text)
        if mo:
            item_in_list_pos = int(mo.group(1)) - 1
            text_fragment = mo.group(2)
            if not text_fragment or text_fragment == data['items_texts'][item_in_list_pos] or data['items_texts'][item_in_list_pos].startswith(text_fragment[:-3]):
                item_new_status = data['item_new_status']
                items_num = data['items_num']
                if item_in_list_pos < items_num:
                    item_id = data['items_ids'][item_in_list_pos]
                    async with OrmSession() as session:
                        item = await session.get(Item, item_id)
                        item.status = ItemStatus[item_new_status]
                        await session.commit()
                        await message.reply(
                            emojize(text(
                            text(human_item_status[item.status], ':', sep=''),
                            text(':pushpin:', item.text),
                            sep='\n')),
                            reply_markup=types.ReplyKeyboardRemove()
                        )
                        await state.finish()
                else:
                    await message.reply(f'В вашем сегодняшнем плане нет столько пунктов, напишите число от 1 до {items_num}')
            else:
                await message.reply('Укажите, пожалуйста просто порядковый номер без всего, либо нажмите на предложенную кнопку')
