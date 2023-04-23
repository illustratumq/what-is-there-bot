from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.repos import UserRepo, DealRepo
from app.keyboards import Buttons
from app.keyboards.reply.menu import basic_kb


async def my_rating_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user = await user_db.get_user(msg.from_user.id)
    done_deals, rating_deals, rating = await deal_db.calculate_user_rating(user.user_id)
    await msg.answer(user.construct_my_rating(rating, done_deals, rating_deals),
                     reply_markup=basic_kb(([Buttons.menu.about, Buttons.menu.comment], [Buttons.menu.back])))


def setup(dp: Dispatcher):
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_rating, state='*')
