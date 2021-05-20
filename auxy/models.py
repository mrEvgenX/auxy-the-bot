from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON


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
    joined_dt = Column(DateTime(timezone=True))
