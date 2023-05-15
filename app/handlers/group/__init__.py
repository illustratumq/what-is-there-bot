from aiogram import Dispatcher

from app.handlers.group import room, price, cancel, admin


def setup(dp: Dispatcher):
    room.setup(dp)
    price.setup(dp)
    cancel.setup(dp)
    admin.setup(dp)
