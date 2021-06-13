import json
import io
from sqlalchemy.future import select
from aiogram import types
from aiogram.utils.markdown import text, code
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from auxy.db import OrmSession
from auxy.db.models import User, Chat, Project
from auxy.bot import bot
from auxy.utils import PeriodBucketModes
from modular_aiogram_handlers import Blueprint


human_period_bucket_modes = {
    'Ежедневно': PeriodBucketModes.daily,
    'Еженедельно': PeriodBucketModes.weekly,
    'Ежемесячно': PeriodBucketModes.monthly,
    'Ежегодно': PeriodBucketModes.yearly,
    'Никогда': PeriodBucketModes.perpetual,
}


class NewProjectForm(StatesGroup):
    project_name = State()
    project_period_bucket_mode = State()
    project_settigns_file = State()


newproject = Blueprint()


@newproject.message_handler(commands='newproject')
async def start_new_project_creation(message: types.Message):
    await NewProjectForm.project_name.set()
    await message.reply('Напишите короткое имя проекта')


@newproject.message_handler(lambda message: len(message.text) <= 150, state=NewProjectForm.project_name)
async def process_project_name(message: types.Message, user: User, state: FSMContext):
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
            Project.name == message.text,
            Project.owner_user_id == user.id,
        )
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()
        if not project:
            await state.update_data(project_name=message.text)
            await NewProjectForm.next()

            keyboard = [
                [types.KeyboardButton(mode_name)]
                for mode_name in human_period_bucket_modes.keys()
            ]
            await message.reply(
                f'Выберите, когда обновлять списки задач',
                reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard)
            )
        else:
            await message.reply(
                f'Проект "{message.text}" уже существует'
            )


@newproject.message_handler(lambda message: len(message.text) > 150, state=NewProjectForm.project_name)
async def process_project_name_invalid(message: types.Message):
    await message.reply(f'Ваш текст содержит много символов, целых {len(message.text)}, а можно максимум 150')


@newproject.message_handler(lambda message: message.text in human_period_bucket_modes.keys(),
                            state=NewProjectForm.project_period_bucket_mode)
async def process_project_period_bucket_mode(message: types.Message, state: FSMContext):
    await state.update_data(human_period_bucket_mode=message.text)
    await NewProjectForm.next()
    await message.reply(
        f'Теперь пришлите json-файл с настройками для нового проекта',
        reply_markup=types.ReplyKeyboardRemove()
    )


@newproject.message_handler(lambda message: message.text not in human_period_bucket_modes.keys(),
                            state=NewProjectForm.project_period_bucket_mode)
async def process_project_period_bucket_mode_invalid(message: types.Message):
    await message.reply(
        f'Допустимые варианты: {", ".join(human_period_bucket_modes.keys())}. '
        'Пожалуйста, выберите один из них с помощью клавиатуры.'
    )


@newproject.message_handler(content_types=types.ContentType.DOCUMENT, state=NewProjectForm.project_settigns_file)
async def process_project_settigns_file(message: types.Message, user: User, chat: Chat, state: FSMContext):
    dt = message.date
    if message.document['mime_type'] == 'application/json':
        file = await bot.get_file(message.document['file_id'])
        settings = io.BytesIO()
        await file.download(settings)
        s = json.load(settings)
        async with OrmSession() as session:
            async with state.proxy() as data:
                project = Project(
                    owner_user_id=user.id,
                    name=data['project_name'],
                    chat_id=chat.id,
                    period_bucket_mode=human_period_bucket_modes[data['human_period_bucket_mode']],
                    created_dt=dt,
                    settings=s
                )
                session.add(project)
                await session.commit()
                await message.reply(
                    text(
                        text('Проект', project.name, 'создан'),
                        text('Примененные настройки:'),
                        code(json.dumps(s, indent=4, sort_keys=True)),
                        sep='\n'
                    ),
                    parse_mode=types.ParseMode.MARKDOWN
                )
    else:
        await message.reply('Нужен json-файл')
    await state.finish()
