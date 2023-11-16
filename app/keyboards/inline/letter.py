from app.database.models import Letter
from app.keyboards.inline.back import back_bt
from app.keyboards.inline.base import *

letter_cb = CallbackData('lt', 'letter_id', 'action')


def paginate_letter(letters: list[Letter], current_id: int):

    letters_ids = [l.letter_id for l in letters]
    prev_lt = letters_ids[(letters_ids.index(current_id) - 1) % len(letters_ids)]
    next_lt = letters_ids[(letters_ids.index(current_id) - 1) % len(letters_ids)]

    def button_cb(letter_id: int, action: str = 'pag'):
        return dict(callback_data=letter_cb.new(letter_id=letter_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton('◀️', **button_cb(prev_lt, 'prev')),
         # InlineKeyboardButton('Закрити', **button_cb(current_id, 'close')),
         back_bt(text='Закрити', to='letter_close'),
         InlineKeyboardButton('▶️', **button_cb(next_lt, 'next'))]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)