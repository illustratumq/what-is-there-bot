from aiogram import Dispatcher

from app.handlers.admin import post, panel


def setup(dp: Dispatcher):
    post.setup(dp)
    panel.setup(dp)