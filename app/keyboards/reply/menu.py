from app.keyboards.reply.base import *


def menu_kb(admin: bool = False):
    keyboard = [
        [KeyboardButton(Buttons.menu.new_post), KeyboardButton(Buttons.menu.new_deal)],
        [KeyboardButton(Buttons.menu.my_posts), KeyboardButton(Buttons.menu.my_money)],
        [KeyboardButton(Buttons.menu.my_rating), KeyboardButton(Buttons.menu.my_chats)],
        [KeyboardButton(Buttons.menu.notifications)]
    ]

    if admin:
        keyboard[-1].append(KeyboardButton(Buttons.menu.admin))

    return ReplyKeyboardMarkup(
        row_width=2,
        resize_keyboard=True,
        keyboard=keyboard
    )


def basic_kb(buttons: list | tuple):
    return ReplyKeyboardMarkup(
        row_width=max(map(len, buttons)),
        resize_keyboard=True,
        keyboard=[*buttons] if isinstance(buttons[0], list) else [buttons]
    )
