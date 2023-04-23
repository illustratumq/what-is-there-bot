import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database.models.base import BaseModel

log = logging.getLogger(__name__)


async def create_db_engine_and_session_pool(sqlalchemy_url: str, config) -> tuple[AsyncEngine, sessionmaker]:
    engine = create_async_engine(
        sqlalchemy_url,
        query_cache_size=1200,
        pool_size=100,
        max_overflow=200,
        future=True,
        echo=True if config.misc.log_level == 10 else False,
    )

    async with engine.begin() as conn:
        if config.db.reset_db:
            await conn.run_sync(BaseModel.metadata.drop_all)
            log.info('База данних перезаписана...')
        await conn.run_sync(BaseModel.metadata.create_all)
        log.info('Створюю сессію до БД...')

    sqlalchemy_session_pool = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    return engine, sqlalchemy_session_pool
