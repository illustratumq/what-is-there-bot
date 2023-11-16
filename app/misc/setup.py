import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.services.repos import CommissionRepo, AdminSettingRepo

log = logging.getLogger(__name__)


async def setup_default_commission_pack(session: sessionmaker):
    session: AsyncSession = session()
    commission_db = CommissionRepo(session)
    if await commission_db.count() == 0:
        await commission_db.add(
            name='Стандартний комісійний пакет',
            description='Призначається всім користувачам, за замовчуванням',
            commission=5,
            trigger=200,
            minimal=30,
            maximal=15000
        )
        log.info('Створено комісійний пакунок за замовчуванням...')


async def setup_default_admin_settings(session: sessionmaker):
    session: AsyncSession = session()
    admin_setting_db = AdminSettingRepo(session)
    if await admin_setting_db.count() == 0:
        await admin_setting_db.add(
            setting_name='Авторизація для виконавців',
            setting_status=False
        )
        log.info('Створено налаштування адмінстратора за замовчуванням...')