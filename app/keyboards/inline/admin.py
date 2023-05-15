from app.database.models import Deal
from app.keyboards.inline.base import *

admin_room_cb = CallbackData('adr', 'deal_id', 'action')


def admin_command_kb(deal: Deal):

    def button_cb(action: str):
        return dict(callback_data=admin_room_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.admin.done_deal, **button_cb('done_deal')),
         InlineKeyboardButton(Buttons.deal.admin.cancel_deal, **button_cb('cancel_deal'))],
        [InlineKeyboardButton(Buttons.deal.admin.restrict_user, **button_cb('restrict_user')),
         InlineKeyboardButton(Buttons.deal.admin.ban_user, **button_cb('ban_user'))],
        [InlineKeyboardButton(Buttons.deal.admin.close, **button_cb('close'))]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def admin_confirm_kb(deal: Deal, action: str):

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.admin.confirm,
                              callback_data=admin_room_cb.new(deal_id=deal.deal_id, action=f'conf_{action}'))],
        [InlineKeyboardButton(Buttons.deal.admin.back,
                              callback_data=admin_room_cb.new(deal_id=deal.deal_id, action='back'))]
    ]

    return InlineKeyboardMarkup(row_width=1, inline_keyboard=inline_keyboard)
