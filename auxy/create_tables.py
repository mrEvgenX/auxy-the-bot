import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from .models import Base


async def main():
    engine = create_async_engine(
        os.environ['DATABASE_URI'],
        echo=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)



if __name__ == '__main__':
    asyncio.run(main())
