import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dateutil.relativedelta import MO, TU, WE, TH, FR
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
                        'reminder_timings': {
                            MO.weekday: {'hour': 18, 'minute': 30, 'second': 0, 'microsecond': 0},
                            TU.weekday: {'hour': 17, 'minute': 30, 'second': 0, 'microsecond': 0},
                            WE.weekday: {'hour': 16, 'minute': 30, 'second': 0, 'microsecond': 0},
                            TH.weekday: {'hour': 18, 'minute': 30, 'second': 0, 'microsecond': 0},
                            FR.weekday: {'hour': 16, 'minute': 0, 'second': 0, 'microsecond': 0},
                        },
                        'return_tomorrow_agenda_at': {'hour': 9, 'minute': 0, 'second': 0, 'microsecond': 0}
                    }
                )
            ])


if __name__ == '__main__':
    asyncio.run(main())
