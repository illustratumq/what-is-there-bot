from aiogram import Dispatcher

from app.handlers.private import start
from app.handlers.private import post
from app.handlers.private import my_posts
from app.handlers.private import my_chats
from app.handlers.private import participate
from app.handlers.private import markers
from app.handlers.private import room
from app.handlers.private import my_rating
from app.handlers.private import my_balance
from app.handlers.private import pay
from app.handlers.private import evaluate
from app.handlers.private import back
from app.handlers.private import new_deal


def setup(dp: Dispatcher):
    start.setup(dp)
    post.setup(dp)
    new_deal.setup(dp)
    participate.setup(dp)
    room.setup(dp)
    pay.setup(dp)
    markers.setup(dp)
    my_posts.setup(dp)
    my_chats.setup(dp)
    my_rating.setup(dp)
    my_balance.setup(dp)
    evaluate.setup(dp)
    back.setup(dp)
