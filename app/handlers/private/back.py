from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from app.config import Config
from app.database.services.repos import UserRepo, PostRepo, RoomRepo, DealRepo, LetterRepo
from app.handlers.admin.panel import admin_cmd
from app.handlers.admin.statistic_v2 import statistic_cmd
from app.handlers.group.admin import select_user_cmd, back_to_room_cmd
from app.handlers.private.start import start_cmd
from app.keyboards.inline.back import back_cb


async def back_cmd(call: CallbackQuery, callback_data: dict, user_db: UserRepo,
                   post_db: PostRepo, room_db: RoomRepo, deal_db: DealRepo, letter_db: LetterRepo,
                   state: FSMContext, config: Config):

    to = callback_data['to']
    if to == 'help_admin':
        await back_to_room_cmd(call, callback_data, user_db, deal_db, room_db, post_db)
    elif to in ['letter_close', 'menu']:
        await call.message.delete()
        await start_cmd(call.message, state, user_db, letter_db)
    elif to == 'select_user':
        await select_user_cmd(call, callback_data, user_db, deal_db, room_db, post_db)
    elif to == 'admin':
        await call.message.delete()
        await admin_cmd(call.message, state, config)
    elif to == 'stat_main_bar':
        await call.message.delete()
        await statistic_cmd(call.message)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(back_cmd, back_cb.filter(), state='*')
