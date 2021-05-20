import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .settings import DATABASE_URI
from .models import Base, BotSettings


async def main():
    engine = create_async_engine(DATABASE_URI, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as session:
        async with session.begin():
            session.add_all([
                BotSettings(
                    section='end_of_workday_reminder',
                    content={
                        'reminder_text': 'Рабочий день подходит к концу, быть может пора уже закругляться?\n'
                                         'Но перед тем, как закончить, пожалуйста, '
                                         'составьте план на завтра и пришлите его мне.\n'
                                         'Утром я напомню о том, что вы собирались сделать.',
                        'reminder_timings': [

                        ],
                        'return_tomorrow_agenda_at': {
                            'days': 'NEXT_WORK_DAY',
                            'hour': 9,
                            'minute': 0,
                            'second': 0,
                            'microsecond': 0
                        }
                    }
                )
            ])


if __name__ == '__main__':
    asyncio.run(main())
