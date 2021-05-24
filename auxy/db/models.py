from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Table, Column, Integer, String, DateTime, Date, JSON, Text, ForeignKey
from sqlalchemy.schema import UniqueConstraint


Base = declarative_base()


class BotSettings(Base):
    __tablename__ = 'bot_settings'

    section = Column(String(64), primary_key=True)
    content = Column(JSON, nullable=False)


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


item_in_list_table = Table('item_in_list', Base.metadata,
    Column('item_id', Integer, ForeignKey('todo_items.id')),
    Column('list_id', Integer, ForeignKey('daily_todo_lists.id'))
)


class DailyTodoList(Base):
    __tablename__ = 'daily_todo_lists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    created_dt = Column(DateTime(timezone=True), nullable=False)
    for_day = Column(Date, nullable=False)
    items = relationship('TodoItem', secondary=item_in_list_table)
    __table_args__ = (UniqueConstraint('user_id', 'for_day'),)


class TodoItem(Base):
    __tablename__ = 'todo_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    text = Column(Text, nullable=False)
    created_dt = Column(DateTime(timezone=True), nullable=False)
