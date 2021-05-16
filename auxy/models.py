from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(256))
    first_name = Column(String(256))
    last_name = Column(String(256))
    lang = Column(String(64))
    joined = Column(DateTime(timezone=True))
