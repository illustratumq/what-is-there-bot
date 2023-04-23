from aiogram import Dispatcher

from app.handlers.group import room, price, cancel


def setup(dp: Dispatcher):
    room.setup(dp)
    price.setup(dp)
    cancel.setup(dp)
