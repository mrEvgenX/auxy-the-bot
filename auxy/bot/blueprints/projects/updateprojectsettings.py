import json
import io
from sqlalchemy.future import select
from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.utils.markdown import text, code
from auxy.db import OrmSession
from auxy.db.models import User, Project
from auxy.bot import bot
from modular_aiogram_handlers import Blueprint


class UpdateProjectSettingsForm(StatesGroup):
    project_name = State()
    project_settigns_file = State()


updateprojectsettings = Blueprint()


@updateprojectsettings.message_handler(commands='updateprojectsettings')
async def start_project_settings_updating(message: types.Message, user: User):
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
                Project.owner_user_id == user.id,
            )
        projects_result = await session.execute(select_stmt)
        keyboard = []
        for project in projects_result.scalars():
            if not keyboard or len(keyboard[-1]) < 2:
                keyboard.append([])
            keyboard[-1].append(types.KeyboardButton(project.name))
        if keyboard:
            await UpdateProjectSettingsForm.project_name.set()
            await message.reply(
                'Выберите проект',
                reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard)
            )
        else:
            await message.reply('У вас нет проектов')


@updateprojectsettings.message_handler(state=UpdateProjectSettingsForm.project_name)
async def receive_project_name(message: types.Message, user: User, state: FSMContext):
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
                Project.name == message.text,
                Project.owner_user_id == user.id,
            )
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()
        if project:
            await state.update_data(project_id=project.id)
            await UpdateProjectSettingsForm.next()
            await message.reply(
                'Проект ' + message.text + '\nПришлите, пожалуйста, json-файл с настройками',
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply(
                f'Проекта "{message.text}" не существует'
            )


@updateprojectsettings.message_handler(content_types=types.ContentType.DOCUMENT,
                                       state=UpdateProjectSettingsForm.project_settigns_file)
async def receive_new_project_settings(message: types.Message, user: User, state: FSMContext):
    if message.document['mime_type'] == 'application/json':
        file = await bot.get_file(message.document['file_id'])
        settings = io.BytesIO()
        await file.download(settings)
        s = json.load(settings)
        async with OrmSession() as session:
            async with state.proxy() as data:
                project = await session.get(Project, data['project_id'])
            project.settings = s
            await session.commit()
        await message.reply(
            text(
                text('Проект', project.name, 'создан'),
                text('Новые настройки для проекта', project.name),
                code(json.dumps(s, indent=4, sort_keys=True)),
                sep='\n'
            ),
            parse_mode=types.ParseMode.MARKDOWN
        )
    else:
        await message.reply('Нужен json-файл')
    await state.finish()
