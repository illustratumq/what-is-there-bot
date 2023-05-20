from app.keyboards.inline.base import *

back_cb = CallbackData('bk', 'to', 'deal_id', 'user_id')


def back_bt(text: str = Buttons.menu.back, to: str = 'menu', deal_id: int = 0, user_id: int = 0):
    return InlineKeyboardButton(text, callback_data=back_cb.new(to=to, deal_id=deal_id, user_id=user_id))


def back_kb(text: str = Buttons.menu.back, to: str = 'menu', deal_id: int = 0, user_id: int = 0):
    return InlineKeyboardMarkup(row_width=1, inline_keyboard=[[back_bt(text, to, deal_id=deal_id, user_id=user_id)]])
