from aiogram import Dispatcher

from app.handlers.admin import post, panel, edit_post, statistic, database


def setup(dp: Dispatcher):
    post.setup(dp)
    panel.setup(dp)
    edit_post.setup(dp)
    statistic.setup(dp)
    database.setup(dp)
