from app.database.models import Post, User, Deal
from app.keyboards.inline.base import *

moderate_post_cb = CallbackData('mp', 'post_id', 'action', 'admin_id')
public_post_cb = CallbackData('pb', 'admin_id', 'delay', 'action', 'post_id')
comment_deal_cb = CallbackData('cmd', 'action', 'deal_id', 'sort')


def public_all_post_cb(admin: User, post: Post, current_delay: int):

    def button_cb(action: str, delay: int):
        return dict(callback_data=public_post_cb.new(admin_id=admin.user_id, delay=delay,
                                                     action=action, post_id=post.post_id))

    back_cb = moderate_post_cb.new(post_id=post.post_id, action='back', admin_id=admin.user_id)

    inline_keyboard = [
        [InlineKeyboardButton(str(d), **button_cb('set_delay', d)) for d in [10, 20, 30, 40, 60]],
        [
            InlineKeyboardButton('➕ 5', **button_cb('plus_delay', 5)),
            InlineKeyboardButton('➖ 5', **button_cb('minus_delay', 5))
        ],
        [InlineKeyboardButton(Buttons.post.publish_all, **button_cb('publish_all', current_delay))],
        [InlineKeyboardButton(Buttons.post.cancel, callback_data=back_cb)]
    ]

    return InlineKeyboardMarkup(row_width=5, inline_keyboard=inline_keyboard)


def moderate_post_kb(post: Post):

    def button_cb(action: str):
        return moderate_post_cb.new(post_id=post.post_id, action=action, admin_id=0)

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.post.publish.split(' ')[0], callback_data=button_cb('approve')),
             InlineKeyboardButton(Buttons.post.cancel, callback_data=button_cb('cancel'))],
            [InlineKeyboardButton(Buttons.post.publish_all, callback_data=button_cb('publish_all'))]
        ]
    )


async def after_public_edit_kb(post: Post):
    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.post.manage_post, url=await post.manage_link)]
        ]
    )


def confirm_post_moderate(action: str, post: Post, admin: User):

    def button_cb(act: str):
        return moderate_post_cb.new(post_id=post.post_id, action=act, admin_id=admin.user_id)

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.post.confirm, callback_data=button_cb(f'conf_{action}'))],
            [InlineKeyboardButton(Buttons.post.back, callback_data=button_cb('back'))]
        ]
    )

def comment_deal_kb(deals: list[Deal], deal_id: int, sort: str = 'default'):
    deals = [deal.deal_id for deal in deals]
    current_index = deals.index(deal_id)
    next_deal_id = deals[(current_index + 1) % len(deals)]
    prev_deal_id = deals[(current_index - 1) % len(deals)]

    def button_cb(current_deal_id: int, action: str):
        return dict(
            callback_data=comment_deal_cb.new(deal_id=current_deal_id, action=action, sort=sort)
        )

    sort_type_text = {
        'default': 'Вимк', 'max': 'Найкращі', 'min': 'Найгірші'
    }

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.sort.format(sort_type_text[sort]),
                              **button_cb(deal_id, action='sort_switch'))],
        [
            InlineKeyboardButton('◀', **button_cb(prev_deal_id, 'pag')),
            InlineKeyboardButton('Назад', **button_cb(deal_id, 'cancel')),
            InlineKeyboardButton('▶', **button_cb(next_deal_id, 'pag'))
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)