from datetime import timedelta

from babel.dates import format_date

from app.keyboards.inline.back import back_bt
from app.keyboards.inline.base import *
from app.misc.times import now

statistic_cb = CallbackData('st', 'action', 'param', 'bar')


def menu_statistic_kb():

    def button_cb(bar: str):
        return dict(callback_data=statistic_cb.new(action='switch_to', bar=bar, param=''))

    statistic = Buttons.admin.statistic_menu

    inline_keyboard = [
        [InlineKeyboardButton(statistic.finance, **button_cb('finance')),
         InlineKeyboardButton(statistic.users, **button_cb('users'))],
        [InlineKeyboardButton(statistic.deals, **button_cb('deals'))],
        [back_bt(to='admin')]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def statistic_mini_bar(bar: str, param: str):

    def button_cb(action: str, param: str):
        return dict(callback_data=statistic_cb.new(action=action, bar=bar, param=param))

    statistic = Buttons.admin.statistic_menu

    inline_keyboard = [
        [InlineKeyboardButton(statistic.date, **button_cb('date', 'input')),
         InlineKeyboardButton(statistic.update, **button_cb(action='switch_to', param=param))],
        [back_bt(to='stat_main_bar')]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)

def go_to_bar(times: str):
    def button_cb(bar: str):
        return dict(callback_data=statistic_cb.new(action='switch_to', bar=bar, param=times))

    statistic = Buttons.admin.statistic_menu

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton('обрати ' + statistic.finance, **button_cb('finance'))],
        [InlineKeyboardButton('обрати ' + statistic.users, **button_cb('users'))],
        [InlineKeyboardButton('обрати ' + statistic.deals, **button_cb('deals'))],
        [back_bt(to='admin')]
    ])