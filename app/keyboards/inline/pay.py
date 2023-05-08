from app.database.models import Deal
from app.keyboards.inline.base import *

pay_cb = CallbackData('pay', 'deal_id', 'action')


def pay_deal_kb(deal: Deal, balance: bool = False, partially: bool = False):

    def button_cb(action: str):
        return dict(callback_data=pay_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.pay.pay_deal_fully, **button_cb('pay_fully'))
        ]
    ]
    if balance:
        inline_keyboard.insert(
            0, [InlineKeyboardButton(Buttons.pay.pay_deal_balance, **button_cb('pay_from_balance'))]
        )
    elif partially:
        inline_keyboard.insert(
            0, [InlineKeyboardButton(Buttons.pay.pay_deal_partially, **button_cb('pay_partially'))]
        )

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def confirm_pay_kb(deal: Deal, action: str):

    def button_cb(act: str):
        return dict(callback_data=pay_cb.new(deal_id=deal.deal_id, action=act))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.pay.confirm, **button_cb(f'conf_{action}'))],
        [InlineKeyboardButton(Buttons.pay.cancel, **button_cb('cancel_pay'))]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)