import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.services.repos import CommissionRepo

log = logging.getLogger(__name__)


async def setup_default_commission_pack(session: sessionmaker):
    session: AsyncSession = session()
    commission_db = CommissionRepo(session)
    await commission_db.add(
        name='Стандартний комісійний пакет',
        description='Призначається всім користувачам, за замовчуванням',
        commission=5,
        trigger=200,
        minimal=30,
        maximal=15000
    )
    log.info('Створено комісійник пакунок за замовчуванням...')
