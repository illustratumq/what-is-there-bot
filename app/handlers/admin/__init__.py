from aiogram import Dispatcher

from app.handlers.admin import post


def setup(dp: Dispatcher):
    post.setup(dp)
