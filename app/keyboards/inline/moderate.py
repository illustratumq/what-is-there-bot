from app.database.models import Post, User
from app.keyboards.inline.base import *

moderate_post_cb = CallbackData('mp', 'post_id', 'action', 'admin_id')


def moderate_post_kb(post: Post):

    def button_cb(action: str):
        return moderate_post_cb.new(post_id=post.post_id, action=action, admin_id=0)

    return InlineKeyboardMarkup(
        row_width=1,
        inline_keyboard=[
            [InlineKeyboardButton(Buttons.post.publish.split(' ')[0], callback_data=button_cb('approve')),
             InlineKeyboardButton(Buttons.post.cancel, callback_data=button_cb('cancel'))]
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
