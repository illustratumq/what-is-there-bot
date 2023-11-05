from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from app.config import Config
from app.database.services.repos import UserRepo, PostRepo, RoomRepo, DealRepo
from app.handlers.admin.panel import admin_cmd
from app.handlers.group.admin import select_user_cmd, back_to_room_cmd
from app.keyboards.inline.back import back_cb


async def back_cmd(call: CallbackQuery, callback_data: dict, user_db: UserRepo,
                   post_db: PostRepo, room_db: RoomRepo, deal_db: DealRepo,
                   state: FSMContext, config: Config):

    to = callback_data['to']
    if to == 'help_admin':
        await back_to_room_cmd(call, callback_data, user_db, deal_db, room_db, post_db)
    elif to == 'select_user':
        await select_user_cmd(call, callback_data, user_db, deal_db, room_db, post_db)
    elif to == 'admin':
        await call.message.delete()
        await admin_cmd(call.message, state, config)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(back_cmd, back_cb.filter(), state='*')
