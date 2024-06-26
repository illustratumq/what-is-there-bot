from aiogram import Dispatcher

from app.handlers.admin import post, panel, edit_post, statistic, database, users, statistic_v2


def setup(dp: Dispatcher):
    post.setup(dp)
    panel.setup(dp)
    edit_post.setup(dp)
    statistic_v2.setup(dp)
    database.setup(dp)
    users.setup(dp)

