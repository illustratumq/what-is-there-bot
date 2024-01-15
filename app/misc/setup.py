import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.repos import CommissionRepo, AdminSettingRepo, MerchantRepo

log = logging.getLogger(__name__)


async def setup_default_merchants(session: sessionmaker, config: Config):
    session: AsyncSession = session()
    merchant_db = MerchantRepo(session)
    fondy = config.bot
    if await merchant_db.count() == 0:
        await merchant_db.add(merchant_id=fondy.fondy_merchant_id_1, name='Мерчант 10', percent=0.1,
                              secret_key=fondy.fondy_secret_key_1, p2p_key=fondy.fondy_p2p_key_1)
        await merchant_db.add(merchant_id=fondy.fondy_merchant_id_2, name='Мерчант 7', percent=0.07,
                              secret_key=fondy.fondy_secret_key_2, p2p_key=fondy.fondy_p2p_key_2)
        await merchant_db.add(merchant_id=fondy.fondy_merchant_id_3, name='Мерчант 5', percent=0.05,
                              secret_key=fondy.fondy_secret_key_3, p2p_key=fondy.fondy_p2p_key_3)
        log.info('Додано дані про мерчантів...')
    await session.commit()
    await session.close()

async def setup_default_commission_pack(session: sessionmaker, config: Config):
    session: AsyncSession = session()
    commission_db = CommissionRepo(session)
    if await commission_db.count() == 0:
        await commission_db.add(
            name='Стандартний комісійний пакет',
            description='Призначається всім користувачам, за замовчуванням',
            merchant_1=config.bot.fondy_merchant_id_1,
            merchant_2=config.bot.fondy_merchant_id_2,
            merchant_3=config.bot.fondy_merchant_id_3
        )
        log.info('Створено комісійний пакунок за замовчуванням...')
    await session.commit()
    await session.close()


async def setup_default_admin_settings(session: sessionmaker):
    session: AsyncSession = session()
    admin_setting_db = AdminSettingRepo(session)
    if await admin_setting_db.count() == 0:
        await admin_setting_db.add(
            setting_name='Авторизація для виконавців',
            setting_status=False
        )
        log.info('Створено налаштування адмінстратора за замовчуванням...')
    await session.commit()
    await session.close()