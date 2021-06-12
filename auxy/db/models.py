from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy.future import select
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, JSON, Text, ForeignKey
from sqlalchemy.schema import UniqueConstraint


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String(256))
    first_name = Column(String(256))
    last_name = Column(String(256))
    lang = Column(String(64))
    joined_dt = Column(DateTime(timezone=True), nullable=False)
    daily_todo_lists = relationship("DailyTodoList")
    all_todo_items = relationship("TodoItem")
    projects = relationship("Project")

    async def create_new_for_day_with_items_or_append_to_existing(self, session, chat, for_day, now, str_items):
        created = False

        select_stmt = select(Project) \
            .where(
            Project.owner_user_id == self.id,
            Project.chat_id == chat.id
        ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()

        tomorrow_todo_list = await project.get_for_day(session, for_day)
        if not tomorrow_todo_list:
            tomorrow_todo_list = DailyTodoList(
                user_id=self.id,
                project_id=project.id,
                created_dt=now,
                for_day=for_day
            )
            session.add(tomorrow_todo_list)
            created = True
        for str_item in str_items:
            todo_item = TodoItem(
                user_id=self.id,
                project_id=project.id,
                text=str_item,
                created_dt=now
            )
            session.add(todo_item)
            tomorrow_todo_list.items.append(todo_item)
        return created


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True, autoincrement=False)
    type = Column(String(256))
    username = Column(String(256))
    joined_dt = Column(DateTime(timezone=True), nullable=False)


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    chat_id = Column(Integer, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
    settings = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('owner_user_id', 'name'),)

    async def get_for_day(self, session, for_day, with_log_messages=False):
        opts = selectinload(DailyTodoList.items)
        if with_log_messages:
            opts = opts.selectinload(TodoItem.log_messages)
        select_stmt = select(DailyTodoList) \
            .options(opts) \
            .where(
            DailyTodoList.project_id == self.id,
            DailyTodoList.for_day == for_day,
        )
        todo_lists_result = await session.execute(select_stmt)
        return todo_lists_result.scalars().first()

    async def get_since(self, session, start_day, with_log_messages=False):
        opts = selectinload(DailyTodoList.items)
        if with_log_messages:
            opts = opts.selectinload(TodoItem.log_messages)
        select_stmt = select(DailyTodoList) \
            .options(opts) \
            .where(
                DailyTodoList.project_id == self.id,
                DailyTodoList.for_day >= start_day,
            ) \
            .order_by(DailyTodoList.for_day)
        todo_lists_result = await session.execute(select_stmt)
        return todo_lists_result.scalars()


item_in_list_table = Table('item_in_list', Base.metadata,
    Column('item_id', Integer, ForeignKey('todo_items.id')),
    Column('list_id', Integer, ForeignKey('daily_todo_lists.id'))
)


class DailyTodoList(Base):
    __tablename__ = 'daily_todo_lists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    created_dt = Column(DateTime(timezone=True), nullable=False)
    for_day = Column(Date, nullable=False)
    items = relationship('TodoItem', secondary=item_in_list_table)
    __table_args__ = (UniqueConstraint('project_id', 'for_day'),)


class TodoItem(Base):
    __tablename__ = 'todo_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
    log_messages = relationship("TodoItemLogMessage")


class TodoItemLogMessage(Base):
    __tablename__ = 'todo_item_log_messages'

    id = Column(Integer, primary_key=True)
    todo_item_id = Column(Integer, ForeignKey('todo_items.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
