import logging
import os
from datetime import timedelta, datetime
from pprint import pprint

from aiogram import Bot
from aiogram.types import InputFile
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo, CommissionRepo, MarkerRepo, SettingRepo, \
    OrderRepo, JoinRepo, MerchantRepo
from app.fondy.new_api import FondyApiWrapper
from app.handlers.admin.database import save_database, save_database_json
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

    @property
    def commission_db(self):
        return CommissionRepo(self.session)

    @property
    def marker_db(self):
        return MarkerRepo(self.session)

    @property
    def setting_db(self):
        return SettingRepo(self.session)

    @property
    def order_db(self):
        return OrderRepo(self.session)

    @property
    def join_db(self):
        return JoinRepo(self.session)

    @property
    def merchant_db(self):
        return MerchantRepo(self.session)

    async def close(self):
        await self.session.commit()
        await self.session.close()


log = logging.getLogger(__name__)


async def setup_cron_function(scheduler: ContextSchedulerDecorator):
    # scheduler.add_job(
    #    func=send_database, trigger='cron', hour=23, minute=59, name='Бекап бази даних'
    # )
    scheduler.add_job(
        func=checkout_payments, trigger='interval', seconds=30, name='Перевірка платіжок'
    )
    # scheduler.add_job(checking_chat_activity_func, trigger='date', next_run_time=now() + timedelta(seconds=5))
    # scheduler.add_job(
    #    func=checking_chat_activity_func, trigger='interval', seconds=60, name='Перевірка активності чатів'
    # )
    log.info('Cron функції успішно заплановані')


async def checking_chat_activity_func(session: sessionmaker, bot: Bot, userbot: UserbotController, config: Config,
                                      fondy: FondyApiWrapper):
    db = database(session)
    for deal in await db.deal_db.get_deal_status(DealStatusEnum.BUSY):
        if deal.payed == 0 and deal.next_activity_date and localize(deal.next_activity_date) <= now():
            executor = await db.user_db.get_user(deal.executor_id)
            customer = await db.user_db.get_user(deal.customer_id)
            if deal.activity_confirm:
                text = (
                    f'{customer.create_html_link(customer.full_name)} та {executor.create_html_link(executor.full_name)}, '
                    f'ваша угода актуальна?.\n\n'
                    f'Зауважте, якщо впродовж наступних 12 годин, не підтвердити актуальність угоди, '
                    f'вона буде автоматично відмінена.'
                )
                await bot.send_message(deal.chat_id, text, reply_markup=confirm_deal_activity(deal))
                await db.deal_db.update_deal(
                    deal.deal_id, next_activity_date=datetime.now() + timedelta(minutes=config.misc.chat_activity_period),
                    activity_confirm=False)
            else:
                post = await db.post_db.get_post(deal.post_id)
                room = await db.room_db.get_room(deal.chat_id)
                message = f'<i>Угода "{post.title}" ({room.name}) була відмінена автоматично, через неактивність у чаті.</i>'
                bot.set_current(bot)
                await cancel_deal_processing(bot, deal, None, userbot, config, fondy, session, message=message,
                                             reset_state=False)


async def checkout_payments(session: sessionmaker, bot: Bot, fondy: FondyApiWrapper):
    db = database(session)
    for order in await db.order_db.get_orders_to_check():
        merchant = await db.merchant_db.get_merchant(order.merchant_id)
        response = await fondy.check_order(order, merchant)
        if response['response']['order_status'] == 'approved':
            # actual_amount = int(response['response']['actual_amount']) / 100
            amount = int(int(response['response']['amount']) / 100)
            await db.order_db.update_order(order.id, request_answer=dict(response))
            deal = await db.deal_db.get_deal(order.deal_id)
            executor = await db.user_db.get_user(deal.executor_id)
            customer = await db.user_db.get_user(deal.customer_id)
            await deal.create_log(db.deal_db, f'Угода оплачена через платіжну систему {amount} грн. ({order.id=})')
            await db.deal_db.update_deal(deal.deal_id, payed=deal.payed + amount)
            text = (
                '<b>Угода успішно оплачена</b>\n\n'
                f'{executor.create_html_link(executor.full_name)}, можете приступати до роботи. '
                f'{customer.create_html_link(customer.full_name)}, очікуйте на рішення.'
            )
            text_to_customer = (
                f'Платіж за угоду №{deal.deal_id} проведено успішно'
            )
            await bot.send_message(chat_id=deal.chat_id, text=text)
            await bot.send_message(chat_id=customer.user_id, text=text_to_customer)


async def send_database(session: sessionmaker, bot: Bot, config: Config):
    db = database(session)
    path = await save_database(db.user_db, db.deal_db, db.post_db, db.room_db, db.commission_db,
                               db.join_db, db.setting_db, db.order_db, db.marker_db)
    await bot.send_document(chat_id=config.misc.database_channel_id, document=InputFile(path))
    os.remove(path)
    path = await save_database_json(db.user_db, db.deal_db, db.post_db, db.room_db, db.commission_db,
                                    db.join_db, db.setting_db, db.order_db, db.marker_db)
    await bot.send_document(chat_id=config.misc.database_channel_id, document=InputFile(path))
    os.remove(path)
