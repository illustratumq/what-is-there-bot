from app.database.models import Deal
from app.keyboards.inline.base import *

deal_cb = CallbackData('dl', 'deal_id', 'executor_id', 'action')


def send_deal_kb(deal: Deal, executor_id: int):

    def button_cb(action: str):
        return dict(callback_data=deal_cb.new(deal_id=deal.deal_id, executor_id=executor_id, action=action))

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.post.send_deal, **button_cb('send')),
             InlineKeyboardButton(Buttons.post.cancel, **button_cb('close'))]
        ]
    )


def moderate_deal_kb(deal: Deal, executor_id: int):

    def button_cb(action: str):
        return dict(callback_data=deal_cb.new(deal_id=deal.deal_id, executor_id=executor_id, action=action))

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.deal.chat, **button_cb('chat')),
             InlineKeyboardButton(Buttons.deal.cancel, **button_cb('cancel'))]
        ]
    )


def join_room_kb(invite_link: str):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton('Увійти до кімнати 🔐', url=invite_link)]
        ]
    )
