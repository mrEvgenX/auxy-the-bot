from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy.future import select
from sqlalchemy import Table, Column, Integer, String, DateTime, JSON, Text, ForeignKey, Enum, BigInteger
from sqlalchemy.schema import UniqueConstraint
from auxy.utils import PeriodBucket, PeriodBucketModes, ItemStatus


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    username = Column(String(256))
    first_name = Column(String(256))
    last_name = Column(String(256))
    lang = Column(String(64))
    joined_dt = Column(DateTime(timezone=True), nullable=False)
    projects = relationship("Project")


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    type = Column(String(256))
    username = Column(String(256))
    joined_dt = Column(DateTime(timezone=True), nullable=False)


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False)
    owner_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
    period_bucket_mode = Column(Enum(PeriodBucketModes))
    settings = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('owner_user_id', 'name', name='projects_owner_user_id_name_key'),)

    async def get_for_period(self, session, period_bucket: PeriodBucket, with_log_messages=False):
        opts = selectinload(ItemsList.items.and_(Item.status == ItemStatus.active))
        if with_log_messages:
            opts = opts.selectinload(Item.notes)
        select_stmt = select(ItemsList) \
            .options(opts) \
            .where(
                ItemsList.project_id == self.id,
                ItemsList.period_bucket_key == period_bucket.key(),
            )
        items_lists_result = await session.execute(select_stmt)
        return items_lists_result.scalars().first()

    async def get_since(self, session, start_day: PeriodBucket, with_log_messages=False):
        opts = selectinload(ItemsList.items)
        if with_log_messages:
            opts = opts.selectinload(Item.notes)
        select_stmt = select(ItemsList) \
            .options(opts) \
            .where(
                ItemsList.project_id == self.id,
                ItemsList.period_bucket_key >= start_day.key(),
            ) \
            .order_by(ItemsList.period_bucket_key)
        items_lists_result = await session.execute(select_stmt)
        return items_lists_result.scalars()

    async def create_new_for_period_with_items_or_append_to_existing(self, session, period: PeriodBucket, now, str_items):
        created = False

        items_list = await self.get_for_period(session, period)
        if not items_list:
            items_list = ItemsList(
                project_id=self.id,
                created_dt=now,
                period_bucket_key=period.key()
            )
            session.add(items_list)
            created = True
        for str_item in str_items:
            item = Item(
                project_id=self.id,
                text=str_item,
                created_dt=now
            )
            session.add(item)
            items_list.items.append(item)
        return created


item_in_list_table = Table('item_in_list', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id')),
    Column('list_id', Integer, ForeignKey('items_lists.id'))
)


class ItemsList(Base):
    __tablename__ = 'items_lists'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    created_dt = Column(DateTime(timezone=True), nullable=False)
    period_bucket_key = Column(String(32))
    items = relationship('Item', secondary=item_in_list_table)
    __table_args__ = (
        UniqueConstraint(
            'project_id',
            'period_bucket_key',
            name='items_lists_project_id_period_bucket_key_key'
        ),
    )


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'))
    text = Column(Text, nullable=False)
    status = Column(Enum(ItemStatus), default=ItemStatus.active)
    created_dt = Column(DateTime(timezone=True), nullable=False)
    notes = relationship("ItemNote")


class ItemNote(Base):
    __tablename__ = 'item_notes'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
