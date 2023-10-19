import logging
import os
from datetime import timedelta, datetime

from aiogram import Bot
from aiogram.types import InputFile
from apscheduler_di import ContextSchedulerDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.database.services.enums import DealStatusEnum, OrderStatusEnum
from app.database.services.repos import DealRepo, UserRepo, PostRepo, RoomRepo, CommissionRepo, MarkerRepo, SettingRepo, \
    OrderRepo, JoinRepo
from app.fondy.api import FondyApiWrapper
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

    async def close(self):
        await self.session.commit()
        await self.session.close()


log = logging.getLogger(__name__)


def setup_cron_function(scheduler: ContextSchedulerDecorator):
    #scheduler.add_job(
    #    func=send_database, trigger='cron', hour=23, minute=59, name='Бекап бази даних'
    #)
    # scheduler.add_job(
    #     func=checkout_payments, trigger='interval', seconds=10, name='Перевірка платіжок'
    # )
    # scheduler.add_job(checking_chat_activity_func, trigger='date', next_run_time=now() + timedelta(seconds=5))
    # scheduler.add_job(
    #    func=checking_chat_activity_func, trigger='interval', seconds=60, name='Перевірка активності чатів'
    # )
    log.info('Функції додані в cron...')


async def checking_chat_activity_func(session: sessionmaker, bot: Bot, userbot: UserbotController, config: Config):
    db = database(session)
    for deal in await db.deal_db.get_deal_status(DealStatusEnum.BUSY):
        if deal.payed == 0 and deal.next_activity_date and localize(deal.next_activity_date) <= now():
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
                await db.deal_db.update_deal(
                    deal.deal_id, next_activity_date=datetime.now() + timedelta(minutes=config.misc.chat_activity_period),
                    activity_confirm=False)
            else:
                post = await db.post_db.get_post(deal.post_id)
                message = (
                    f'Угода "{post.title}" була відмінена автоматично, через неактивність у чаті.'
                )
                bot.set_current(bot)
                await cancel_deal_processing(bot, deal, post, customer, None, db.deal_db, db.post_db, db.user_db,
                                             db.room_db, db.commission_db, db.join_db, userbot, config, message=message,
                                             reset_state=False)


async def checkout_payments(session: sessionmaker, bot: Bot, fondy: FondyApiWrapper):
    db = database(session)
    for order in await db.order_db.get_orders_status(OrderStatusEnum.PROCESSING):
        response = (await fondy.check_order(order))['response']
        # deal = await db.deal_db.get_deal(order.deal_id)
        if response['order_status'] == 'approved':
            # deal = await db.deal_db.get_deal(order.deal_id)
            # answer = await fondy.make_capture(order, deal.price)
            # await bot.send_message(deal.chat_id, answer)
            deal = await db.deal_db.get_deal(int(response['merchant_data']))
            executor = await db.user_db.get_user(deal.executor_id)
            customer = await db.user_db.get_user(deal.customer_id)
            need_to_pay = int(int(response['actual_amount']) / 100)
            if 'pay_from_balance' in order.body.keys():
                need_to_pay += int(order.body['pay_from_balance'])
            commission_package = await db.commission_db.get_commission(customer.commission_id)
            commission = commission_package.deal_commission(deal)
            post = await db.post_db.get_post(deal.post_id)
            await db.deal_db.update_deal(deal.deal_id, payed=deal.payed + need_to_pay - commission,
                                         commission=deal.commission + commission)
            text_to_chat = (
                f'🔔 Угода була успішно сплачена, кошти зберігаються на балансі сервісу. '
                f'{executor.create_html_link("Виконавець")} можете приступати до роботи!'
            )
            text_to_executor = (
                f'🔔 Замовник оплатив угоду "{post.title}", можете приступати до виконання завдання.'
            )
            text_to_customer = (
                f'✅ Угода успішно оплачена'
            )
            await bot.send_message(deal.customer_id, text_to_customer)
            await bot.send_message(deal.executor_id, text_to_executor)
            await bot.send_message(deal.chat_id, text_to_chat)
            await db.order_db.update_order(order.id, status=OrderStatusEnum.APPROVED)


async def send_database(session: sessionmaker, bot: Bot, config: Config):
    db = database(session)
    path = await save_database(db.user_db, db.deal_db, db.post_db, db.room_db)
    await bot.send_document(chat_id=config.misc.database_channel_id, document=InputFile(path))
    os.remove(path)
    path = await save_database_json(db.user_db, db.deal_db, db.post_db, db.room_db, db.commission_db,
                                    db.marker_db, db.setting_db)
    await bot.send_document(chat_id=config.misc.database_channel_id, document=InputFile(path))
    os.remove(path)