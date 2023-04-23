from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.repos import UserRepo
from app.keyboards import Buttons
from app.keyboards.reply.menu import basic_kb


async def my_balance_cmd(msg: Message, user_db: UserRepo):
    user = await user_db.get_user(msg.from_user.id)
    await msg.answer(f'Ваш баланс {user.balance} грн',
                     reply_markup=basic_kb(([Buttons.menu.payout], [Buttons.menu.back])))


def setup(dp: Dispatcher):
    dp.register_message_handler(my_balance_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_money, state='*')
