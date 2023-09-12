from app.keyboards.inline.back import back_bt
from app.keyboards.inline.base import *

statistic_cb = CallbackData('st', 'action', 'date', 'back')


def menu_statistic_kb(date: str = 'today'):

    def button_cb(action: str):
        return dict(callback_data=statistic_cb.new(action=action, date=date, back='admin'))

    statistic = Buttons.admin.statistic_menu

    inline_keyboard = [
        [InlineKeyboardButton(statistic.posts, **button_cb('posts')),
         InlineKeyboardButton(statistic.deals, **button_cb('deals'))],
        [InlineKeyboardButton(statistic.users, **button_cb('users')),
         InlineKeyboardButton(statistic.finance, **button_cb('finance'))],
        [back_bt(to='admin')]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)

def statistic_date_kb(back_to: str, current_date: str, only_back: bool = False):

    def button_cb(date: str, act: str = back_to):
        return dict(callback_data=statistic_cb.new(action=act, date=date, back=back_to))

    statistic = Buttons.admin.statistic_menu.date_menu
    inline_keyboard = [
        [InlineKeyboardButton(statistic.day, **button_cb('today'))],
        [InlineKeyboardButton(statistic.week, **button_cb('week')),
         InlineKeyboardButton(statistic.month, **button_cb('month'))],
        [InlineKeyboardButton(statistic.select_date, **button_cb('custom', 'date'))],
        [InlineKeyboardButton(Buttons.menu.back, **button_cb(current_date, back_to))]
    ]
    if only_back:
        inline_keyboard = [inline_keyboard[-1]]
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)

def statistic_navigate_kb(update: str, date: str = 'today'):

    def button_cb(action: str):
        return dict(callback_data=statistic_cb.new(action=action, date=date, back=update))

    statistic = Buttons.admin.statistic_menu

    return InlineKeyboardMarkup(
        row_width=2,
        inline_keyboard=[
            [InlineKeyboardButton(statistic.date, **button_cb('date')),
             InlineKeyboardButton(statistic.update, **button_cb(update))],
            [back_bt(to='statistic')]
        ]
    )