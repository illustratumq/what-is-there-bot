import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.services.enums import UserTypeEnum
from app.database.services.repos import UserRepo

log = logging.getLogger(__name__)


async def set_admin_status(session: sessionmaker, config):
    session: AsyncSession = session()
    user_db = UserRepo(session)
    for admin_id in config.bot.admin_ids:
        user = await user_db.get_user(admin_id)
        if user and user.type != UserTypeEnum.ADMIN:
            await user_db.update_user(admin_id, type=UserTypeEnum.ADMIN)
    await session.commit()
    await session.close()
