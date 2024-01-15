from app.database.models import Deal
from app.keyboards.inline.base import *

pay_cb = CallbackData('pay', 'deal_id', 'action')
payout_cb = CallbackData('pout', 'user_id', 'card', 'action')

def pay_deal_kb(deal: Deal):

    def button_cb(action: str):
        return dict(callback_data=pay_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.pay.pay_deal_fully, **button_cb('pay_fully'))
        ]
    ]
    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def confirm_pay_kb(deal: Deal, action: str):

    def button_cb(act: str):
        return dict(callback_data=pay_cb.new(deal_id=deal.deal_id, action=act))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.pay.confirm, **button_cb(f'conf_{action}'))],
        [InlineKeyboardButton(Buttons.pay.cancel, **button_cb('cancel_pay'))]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def payout_kb(cards: list[str], user_id: int):

    def button_cb(card: str, action: str = 'payout'):
        return dict(callback_data=payout_cb.new(user_id=user_id, card=card, action=action))

    inline_keyboard = []
    for card in cards:
        inline_keyboard.append(
            [InlineKeyboardButton(card, **button_cb(card))]
        )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=1)
