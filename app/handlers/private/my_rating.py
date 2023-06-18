from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.repos import UserRepo, DealRepo
from app.keyboards import Buttons
from app.keyboards.reply.menu import basic_kb
from app.states.states import UserAboutSG


async def my_rating_cmd(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user = await user_db.get_user(msg.from_user.id)
    await msg.answer(await user.construct_my_rating(deal_db),
                     reply_markup=basic_kb(([Buttons.menu.about, Buttons.menu.comment], [Buttons.menu.back])))


async def add_user_about(msg: Message):
    text = (
        'Будь ласка напишіть короткий опис про себе (до 500 символів)'
    )
    await msg.answer(text, reply_markup=basic_kb([Buttons.menu.to_rating]))
    await UserAboutSG.Input.set()


async def save_user_about(msg: Message, user_db: UserRepo, deal_db: DealRepo):
    user_about = msg.html_text
    if len(user_about) > 500:
        error_text = (
            f'Максимальна к-ть символів 500, замість {len(user_about)}, спробуй ще раз'
        )
        await msg.answer(error_text)
        return
    await user_db.update_user(msg.from_user.id, description=user_about)
    await my_rating_cmd(msg, user_db, deal_db)


# async def view_my_comments_cmd(msg: Message, deal_db: DealRepo):

def setup(dp: Dispatcher):
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.to_rating, state='*')
    dp.register_message_handler(my_rating_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_rating, state='*')
    dp.register_message_handler(add_user_about, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.about, state='*')
    dp.register_message_handler(save_user_about, ChatTypeFilter(ChatType.PRIVATE), state=UserAboutSG.Input)