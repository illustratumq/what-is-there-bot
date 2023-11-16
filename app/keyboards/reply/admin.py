from app.keyboards.reply.base import *


def admin_kb():

    keyboard = [
        [KeyboardButton(Buttons.admin.statistic), KeyboardButton(Buttons.admin.setting)],
        [KeyboardButton(Buttons.admin.user), KeyboardButton(Buttons.admin.menu)]
    ]

    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, keyboard=keyboard)


def construct_packs_kb(packs: list[str]):
    keyboard = []
    for pack in packs:
        keyboard.append([KeyboardButton(pack)])
    keyboard.append([KeyboardButton(Buttons.admin.to_admin)])
    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, keyboard=keyboard)


def keyboard_constructor(*buttons: list[str] | str):
    if len(buttons) == 1:
        keyboard = [[KeyboardButton(buttons[0])]]
    else:
        keyboard = [*buttons]
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)


def edit_commission_kb():
    keyboard = [
        [KeyboardButton(Buttons.admin.commission_edit.name),
         KeyboardButton(Buttons.admin.commission_edit.description)],
        [KeyboardButton(Buttons.admin.commission_edit.trigger),
         KeyboardButton(Buttons.admin.commission_edit.commission)],
        [KeyboardButton(Buttons.admin.commission_edit.under),
         KeyboardButton(Buttons.admin.commission_edit.minimal)],
        [KeyboardButton(Buttons.admin.commission_edit.maximal),
         KeyboardButton(Buttons.admin.cancel)]
    ]
    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, keyboard=keyboard)




