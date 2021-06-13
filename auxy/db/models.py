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
    items_lists = relationship("ItemsList")
    all_items = relationship("Item")
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

        items_list = await project.get_for_day(session, for_day)
        if not items_list:
            items_list = ItemsList(
                user_id=self.id,
                project_id=project.id,
                created_dt=now,
                for_day=for_day
            )
            session.add(items_list)
            created = True
        for str_item in str_items:
            item = Item(
                user_id=self.id,
                project_id=project.id,
                text=str_item,
                created_dt=now
            )
            session.add(item)
            items_list.items.append(item)
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
    __table_args__ = (UniqueConstraint('owner_user_id', 'name', name='projects_owner_user_id_name_key'),)

    async def get_for_day(self, session, for_day, with_log_messages=False):
        opts = selectinload(ItemsList.items)
        if with_log_messages:
            opts = opts.selectinload(Item.notes)
        select_stmt = select(ItemsList) \
            .options(opts) \
            .where(
                ItemsList.project_id == self.id,
                ItemsList.for_day == for_day,
            )
        items_lists_result = await session.execute(select_stmt)
        return items_lists_result.scalars().first()

    async def get_since(self, session, start_day, with_log_messages=False):
        opts = selectinload(ItemsList.items)
        if with_log_messages:
            opts = opts.selectinload(Item.notes)
        select_stmt = select(ItemsList) \
            .options(opts) \
            .where(
                ItemsList.project_id == self.id,
                ItemsList.for_day >= start_day,
            ) \
            .order_by(ItemsList.for_day)
        items_lists_result = await session.execute(select_stmt)
        return items_lists_result.scalars()


item_in_list_table = Table('item_in_list', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id')),
    Column('list_id', Integer, ForeignKey('items_lists.id'))
)


class ItemsList(Base):
    __tablename__ = 'items_lists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    created_dt = Column(DateTime(timezone=True), nullable=False)
    for_day = Column(Date, nullable=False)
    items = relationship('Item', secondary=item_in_list_table)
    __table_args__ = (UniqueConstraint('project_id', 'for_day', name='items_lists_project_id_for_day_key'),)


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
    notes = relationship("ItemNote")


class ItemNote(Base):
    __tablename__ = 'item_notes'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
