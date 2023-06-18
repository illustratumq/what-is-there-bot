from app.database.models import Post, User
from app.keyboards.inline.base import *

post_cb = CallbackData('pt', 'post_id', 'action')


def participate_kb(url: str):
    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=[[InlineKeyboardButton(Buttons.post.participate, url=url)]])


def construct_posts_list_kb(posts: list[Post]):

    def button_cb(p: Post):
        return dict(callback_data=post_cb.new(post_id=p.post_id, action='edit'))

    inline_keyboard = []
    for post, num in zip(posts, range(1, len(posts) + 1)):
        inline_keyboard.append([InlineKeyboardButton(f'Пост {num}', **button_cb(post))])

    inline_keyboard.append([InlineKeyboardButton(
        Buttons.post.back, callback_data=post_cb.new(post_id=0, action='back')
    )])

    return InlineKeyboardMarkup(
        row_width=5, inline_keyboard=inline_keyboard
    )


def moderate_post_kb(post: Post, edit: bool = True, delete: bool = True):

    def button_cb(action: str):
        return dict(callback_data=post_cb.new(post_id=post.post_id, action=action))

    inline_keyboard = []

    if edit:
        inline_keyboard.insert(0, [
            InlineKeyboardButton(Buttons.post.update, **button_cb('update'))
        ])
    if delete:
        inline_keyboard.insert(0, [
            InlineKeyboardButton(Buttons.post.delete, **button_cb('delete'))
        ])

    inline_keyboard.append(
        [InlineKeyboardButton(Buttons.post.back, callback_data=post_cb.new(post_id=post.post_id, action='back_list'))])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)


def delete_post_kb(post: Post):

    def button_cb(action: str):
        return dict(callback_data=post_cb.new(post_id=post.post_id, action=action))

    inline_keyboard = [
        [
            InlineKeyboardButton(Buttons.action.delete, **button_cb('conf_delete')),
        ],
        [
            InlineKeyboardButton(Buttons.post.back, **button_cb('edit'))
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)
