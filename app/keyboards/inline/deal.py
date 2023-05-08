from app.database.models import Deal
from app.keyboards.inline.base import *

deal_cb = CallbackData('dl', 'deal_id', 'executor_id', 'action')
comment_cb = CallbackData('cm', 'original_id', 'deal_id', 'executor_id', 'action', 'sort')


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


def moderate_deal_kb(deal: Deal, executor_id: int, is_comment_deals: list):

    def button_cb(action: str):
        return dict(callback_data=deal_cb.new(deal_id=deal.deal_id, executor_id=executor_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.chat, **button_cb('chat')),
         InlineKeyboardButton(Buttons.deal.cancel, **button_cb('cancel'))]
    ]

    if is_comment_deals:

        def button_c_cb(action: str):
            return dict(
                callback_data=comment_cb.new(original_id=deal.deal_id, executor_id=executor_id, action=action,
                                             deal_id=deal.deal_id, sort='None'))

        inline_keyboard.insert(0, [
            InlineKeyboardButton(Buttons.deal.read_comments, **button_c_cb('start'))
        ])

    return InlineKeyboardMarkup(row_width=1, inline_keyboard=inline_keyboard)


def pagination_deal_kb(executor_id: int, deals_id: list[int], current_deal_id: int, original_id: int, sort: str = 'None'):

    def calculate_index(plus: bool = True):
        if plus:
            index = deals_id.index(current_deal_id) + 3
            if index >= len(deals_id):
                index = 0
        else:
            index = deals_id.index(current_deal_id) - 3
            if index - 3 < len(deals_id):
                index = 0
        return index

    next_deal_set_id = deals_id[calculate_index()]
    prev_deal_set_id = deals_id[calculate_index(False)]

    sort_type_text = {
        'None': 'Вимк', 'max': 'Найкращі', 'min': 'Найгірші'
    }

    def button_cb(set_id: int = original_id, action: str = 'pag'):
        return dict(
            callback_data=comment_cb.new(original_id=original_id, deal_id=set_id, executor_id=executor_id, action=action,
                                         sort=sort))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.sort.format(sort_type_text[sort]),
                              **button_cb(action='sort'))],
        [InlineKeyboardButton('◀', **button_cb(set_id=prev_deal_set_id)),
         InlineKeyboardButton('Назад', **button_cb(action='back')),
         InlineKeyboardButton('▶', **button_cb(set_id=next_deal_set_id))]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def join_room_kb(invite_link: str):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton('Увійти до кімнати 🔐', url=invite_link)]
        ]
    )


async def to_bot_kb(url: str = None):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton('Перейти до оплати', url=url)]
        ]
    )
