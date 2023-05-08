import logging
from datetime import timedelta, datetime

from aiogram import Bot
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo
from app.handlers.group.cancel import cancel_deal_processing
from app.handlers.userbot import UserbotController
from app.keyboards.inline.chat import confirm_deal_activity
from app.misc.times import localize, now


class database:

    def __init__(self, session: sessionmaker):
        self.session: AsyncSession = session()

    @property
    def deal_db(self):
        return DealRepo(self.session)

    @property
    def user_db(self):
        return UserRepo(self.session)

    @property
    def post_db(self):
        return PostRepo(self.session)

    @property
    def room_db(self):
        return RoomRepo(self.session)

    async def close(self):
        await self.session.commit()
        await self.session.close()


log = logging.getLogger(__name__)


def setup_cron_function(scheduler: ContextSchedulerDecorator):
    scheduler.add_job(
        func=checking_chat_activity_func, trigger='interval', seconds=60, name='Перевірка активності чатів'
    )
    log.info('Функції додані в cron...')


async def checking_chat_activity_func(session: sessionmaker, bot: Bot, userbot: UserbotController, config: Config):
    db = database(session)
    for deal in await db.deal_db.get_deal_status(DealStatusEnum.BUSY):
        if localize(deal.next_activity_date) <= now():
            executor = await db.user_db.get_user(deal.executor_id)
            customer = await db.user_db.get_user(deal.customer_id)
            if deal.activity_confirm:
                text = (
                    f'{customer.create_html_link("Замовник")} та {executor.create_html_link("Виконавець")}, '
                    f'угода не була оплачена. Підтвердіть акутальність угоди.\n\n'
                    f'Зауважте, якщо впродовж наступних 12 годин, не підтвердити актуальність угоди, '
                    f'вона буде автоматично відмінена.'
                )
                await bot.send_message(deal.chat_id, text, reply_markup=confirm_deal_activity(deal))
                await db.deal_db.update_deal(deal.deal_id, next_activity_date=datetime.now() + timedelta(seconds=30),
                                             activity_confirm=False)
            else:
                post = await db.post_db.get_post(deal.post_id)
                message = (
                    f'Угода "{post.title}" була відмінена автоматично, через неактивність у чаті.'
                )
                bot.set_current(bot)
                await cancel_deal_processing(bot, deal, post, customer, None, db.deal_db, db.post_db, db.user_db,
                                             db.room_db, userbot, config, message=message, reset_state=False)

