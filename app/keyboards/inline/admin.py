from app.database.models import Deal, Setting, Post
from app.keyboards.inline.back import back_bt
from app.keyboards.inline.base import *

admin_room_cb = CallbackData('adr', 'deal_id', 'action')
user_search_cb = CallbackData('usr', 'user_id', 'action')
user_setting_cb = CallbackData('ust', 'deal_id', 'user_id', 'action')
manage_post_cb = CallbackData('mg', 'post_id', 'action')


def admin_command_kb(deal: Deal):

    def button_cb(action: str):
        return dict(callback_data=admin_room_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.admin.done_deal, **button_cb('done_deal')),
         InlineKeyboardButton(Buttons.deal.admin.cancel_deal, **button_cb('cancel_deal'))],
        [InlineKeyboardButton(Buttons.deal.admin.restrict_user, **button_cb('restrict_user'))],
        # [InlineKeyboardButton(Buttons.deal.admin.close, **button_cb('close'))]
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


def admin_choose_user_kb(deal: Deal):

    def button_cb(action: str):
        return dict(callback_data=admin_room_cb.new(deal_id=deal.deal_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.admin.customer, **button_cb('restrict_customer')),
         InlineKeyboardButton(Buttons.deal.admin.executor, **button_cb('restrict_executor'))],
        [back_bt(to='help_admin', deal_id=deal.deal_id)]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def user_setting_kb(deal: Deal, setting: Setting):

    def button_cb(action: str):
        return dict(callback_data=user_setting_cb.new(deal_id=deal.deal_id, action=action, user_id=setting.user_id))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.deal.admin.ban_user, **button_cb('ban_user'))],
        [InlineKeyboardButton(setting.format('Може бути замовником', setting.can_be_customer),
                              **button_cb('can_be_customer'))],
        [InlineKeyboardButton(setting.format('Може бути виконавцем', setting.can_be_executor),
                              **button_cb('can_be_executor'))],
        [InlineKeyboardButton(setting.format('Може публікувати пости', setting.can_publish_post),
                              **button_cb('can_publish_post'))],
        [InlineKeyboardButton(setting.format('Перевіряти пости', setting.need_check_post),
                              **button_cb('need_check_post'))],
        [back_bt(to='select_user', deal_id=deal.deal_id)]

    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def manage_post_kb(post: Post):

    def button_cb(action: str):
        return dict(callback_data=manage_post_cb.new(post_id=post.post_id, action=action))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.admin.post.delete, **button_cb('delete')),
         InlineKeyboardButton(Buttons.admin.post.server, url=post.server_url)],
        [InlineKeyboardButton(Buttons.admin.post.delete_comment, **button_cb('delete_comment')),
         InlineKeyboardButton(Buttons.admin.post.delete_rating, **button_cb('delete_rating'))],
        [InlineKeyboardButton(Buttons.admin.post.back, **button_cb('close'))]
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=inline_keyboard)


def confirm_moderate_post_kb(post: Post, action: str):

    def button_cb(act: str):
        return dict(callback_data=manage_post_cb.new(post_id=post.post_id, action=act))

    inline_keyboard = [
        [InlineKeyboardButton(Buttons.chat.confirm, **button_cb(f'conf_{action}'))],
        [InlineKeyboardButton(Buttons.admin.post.back, **button_cb('back'))]
    ]

    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=inline_keyboard
    )


def user_info_kb(user_id: int):

    def button_cb(action: str):
        return dict(callback_data=user_search_cb.new(user_id=user_id, action=action))

    return InlineKeyboardMarkup(
        row_width=1, inline_keyboard=[
            [InlineKeyboardButton(Buttons.admin.user_detail, **button_cb('info'))]
        ]
    )
