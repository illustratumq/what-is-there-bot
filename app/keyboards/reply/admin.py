from app.keyboards.reply.base import *


def admin_kb():

    keyboard = [
        [KeyboardButton(Buttons.admin.statistic), KeyboardButton(Buttons.admin.commission)],
        [KeyboardButton(Buttons.admin.commission), KeyboardButton(Buttons.admin.setting)],
        [KeyboardButton(Buttons.admin.menu)]
    ]

    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, keyboard=keyboard)


def construct_packs_kb(packs: list[str]):
    keyboard = []
    for pack in packs:
        keyboard.append([KeyboardButton(pack)])
    keyboard.append([KeyboardButton(Buttons.admin.back)])
    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, keyboard=keyboard)











