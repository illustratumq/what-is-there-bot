import asyncio

import aiogram
import betterlogging as bl
import pyrogram
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.types import ParseMode, AllowedUpdates, BotCommand

from app import handlers, middlewares
from app.database.services.db_engine import create_db_engine_and_session_pool
from app.fondy.new_api import FondyApiWrapper
from app.handlers.userbot import UserbotController
from app.misc.admin import set_admin_status
from app.misc.cron import setup_cron_function
from app.misc.scheduler import compose_scheduler
from app.misc.setup import *
from app.misc.times import now

log = logging.getLogger(__name__)
# logging.getLogger('apscheduler').setLevel(logging.CRITICAL)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand('menu', 'Меню боту'),
        ]
    )
    log.info("Установка комманд пройшла успішно")


async def notify_admin(bot: Bot, userbot: UserbotController, admin_ids: tuple[int]) -> None:
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, f'Бот запущено {now()}')
            await userbot._client.send_message(admin_id, 'Юзербот запущено')
        except aiogram.exceptions.ChatNotFound:
            log.warning(f'Адмін з {admin_id} не ініціалізував чат.')


async def main():
    config = Config.from_env()
    bl.basic_colorized_config(level=config.misc.log_level)
    log.info('Запускаюсь...')

    storage = RedisStorage2(host=config.redis.host, port=config.redis.port)
    bot = Bot(config.bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    db_engine, sqlalchemy_session = await create_db_engine_and_session_pool(config.db.sqlalchemy_url, config)
    userbot = UserbotController(config.userbot, (await bot.me).username, 'app/data/chat.jpg')
    fondy = FondyApiWrapper(sqlalchemy_session)
    scheduler = compose_scheduler(config, bot, sqlalchemy_session, userbot, fondy)

    allowed_updates = (
            AllowedUpdates.MESSAGE + AllowedUpdates.CALLBACK_QUERY +
            AllowedUpdates.EDITED_MESSAGE + AllowedUpdates.CHAT_JOIN_REQUEST +
            AllowedUpdates.PRE_CHECKOUT_QUERY + AllowedUpdates.SHIPPING_QUERY +
            AllowedUpdates.INLINE_QUERY
    )

    environments = dict(config=config, dp=dp, scheduler=scheduler, fondy=fondy, userbot=userbot)
    handlers.setup(dp)
    middlewares.setup(dp, environments, sqlalchemy_session)

    await userbot.connect()
    await setup_cron_function(scheduler)
    await set_bot_commands(bot)
    await setup_default_merchants(sqlalchemy_session, config)
    await setup_default_commission_pack(sqlalchemy_session, config)
    await setup_default_admin_settings(sqlalchemy_session)
    await notify_admin(bot, userbot, config.bot.admin_ids)
    await set_admin_status(sqlalchemy_session, config)

    try:
        scheduler.start()
        await dp.skip_updates()
        await dp.start_polling(allowed_updates=allowed_updates, reset_webhook=True)
    finally:
        await storage.close()
        await storage.wait_closed()
        await (await bot.get_session()).close()
        await db_engine.dispose()
        await userbot._client.stop()

if __name__ == '__main__':

    def get_peer_type(peer_id: int) -> str:
        peer_id_str = str(peer_id)
        if not peer_id_str.startswith("-"):
            return "user"
        elif peer_id_str.startswith("-100"):
            return "channel"
        else:
            return "chat"

    pyrogram.utils.get_peer_type = get_peer_type

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.warning('Бот зупинено')
