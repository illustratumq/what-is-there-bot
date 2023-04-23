from app.database.models import Deal
from app.keyboards.inline.base import *

room_cb = CallbackData('rm', 'deal_id', 'action')
evaluate_cb = CallbackData('ev', 'deal_id', 'action', 'value')


def room_menu_kb(deal: Deal, media: bool = False):

    def button_cb(action: str):
        return dict(callback_data=room_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.chat.pay, **button_cb('pay'))],
        [InlineKeyboardButton(Buttons.chat.edit_price, **button_cb('price'))],
        [InlineKeyboardButton(Buttons.chat.end_deal, **button_cb('end_deal'))],
        [InlineKeyboardButton(Buttons.chat.admin, **button_cb('help'))]
    ]
    if media:
        inline_keyboard.append(
            [InlineKeyboardButton(Buttons.chat.media, **button_cb('send_media'))]
        )

    return InlineKeyboardMarkup(row_width=1, inline_keyboard=inline_keyboard)


def close_deal_kb(deal: Deal):

    def button_cb(action: str):
        return dict(callback_data=room_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.chat.done_deal, **button_cb('done_deal'))],
        [InlineKeyboardButton(Buttons.chat.cancel_deal, **button_cb('cancel_deal'))]
    ]

    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=inline_keyboard
    )


def confirm_moderate_kb(deal: Deal, action: str):

    def button_cb(act: str):
        return dict(callback_data=room_cb.new(deal_id=deal.deal_id, action=act))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.chat.confirm, **button_cb(f'conf_{action}'))],
        [InlineKeyboardButton(Buttons.chat.cancel, **button_cb('back'))]
    ]

    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=inline_keyboard
    )


def evaluate_deal_kb(deal: Deal):

    def button_cb(value: int, action: str = 'eval'):
        return dict(callback_data=evaluate_cb.new(deal_id=deal.deal_id, action=action, value=f'{value}'))

    inline_keyboard = [
        [InlineKeyboardButton(f'{i}⭐', **button_cb(i)) for i in range(1, 6)],
        [InlineKeyboardButton(Buttons.deal.comment, **button_cb(0, 'comment'))],
        [InlineKeyboardButton(Buttons.deal.close, **button_cb(0, 'close'))]
    ]

    return InlineKeyboardMarkup(row_width=1, inline_keyboard=inline_keyboard)