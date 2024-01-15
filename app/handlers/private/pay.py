from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatType

from app.database.services.repos import DealRepo, PostRepo, UserRepo, CommissionRepo, OrderRepo
from app.fondy.api import FondyApiWrapper
from app.keyboards.inline.pay import pay_cb


async def pay_from_fondy_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo, post_db: PostRepo,
                             user_db: UserRepo, commission_db: CommissionRepo, fondy: FondyApiWrapper,
                             order_db: OrderRepo):
    pass


def setup(dp: Dispatcher):
    # dp.register_callback_query_handler(
    #     confirm_pay_deal, ChatTypeFilter(ChatType.PRIVATE),
    #     pay_cb.filter(action=['pay_fully']), state='*'),
    dp.register_callback_query_handler(
        pay_from_fondy_cmd, ChatTypeFilter(ChatType.PRIVATE),
        pay_cb.filter(action=['conf_pay_fully', 'conf_pay_partially']), state='*')
