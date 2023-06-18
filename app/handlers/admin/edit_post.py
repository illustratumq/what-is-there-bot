from aiogram import Dispatcher
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hide_link

from app.config import Config
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import PostRepo, RoomRepo, DealRepo, UserRepo
from app.filters import IsAdminFilter
from app.keyboards.inline.admin import manage_post_cb, manage_post_kb
from app.keyboards.inline.admin import confirm_moderate_post_kb


async def moderate_main_page(call: CallbackQuery, callback_data: dict, post_db: PostRepo, deal_db: DealRepo,
                             room_db: RoomRepo, user_db: UserRepo, config: Config):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    text = (
        f'{post.construct_post_text(use_bot_link=False)}\n\n'
    )
    if post.status == DealStatusEnum.DONE:
        deal = await deal_db.get_deal_post(post_id)
        room = await room_db.get_room(deal.chat_id)
        text += f'🆔 #Угода_номер_{deal.deal_id} завершилась в {room.construct_html_text(room.name)}'
    elif post.status == DealStatusEnum.BUSY:
        deal = await deal_db.get_deal_post(post_id)
        customer = await user_db.get_user(deal.customer_id)
        executor = await user_db.get_user(deal.executor_id)
        text += f'<b>Угода укладена між:</b> {customer.mention} (Замовник) та {executor.mention} (Виконавець)'
    await call.message.edit_text(text, reply_markup=manage_post_kb(post))

async def close_edit_post(call: CallbackQuery):
    await call.answer('Редагування цього поста відмінено', show_alert=True)
    await call.message.delete()


async def confirm_delete_post(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                              deal_db: DealRepo, room_db: RoomRepo):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    deal = await deal_db.get_deal_post(post_id)
    room = await room_db.get_room(deal.chat_id)
    if post.status == DealStatusEnum.BUSY:
        await call.answer(
            f'Цей пост вже оброблюється в {room.name}. Для того щоб його видалити, '
            f'спочатку треба завершити/відмінити угоду', show_alert=True
        )
    else:
        await call.message.edit_text(
            f'Ви бажаєте видалити пост?{hide_link(post.media_url)}\n\nПідвердіть своє рішення',
            reply_markup=confirm_moderate_post_kb(post, action='delete_post')
        )

async def delete_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                          deal_db: DealRepo, room_db: RoomRepo, config: Config):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    deal = await deal_db.get_deal_post(post_id)
    room = await room_db.get_room(deal.chat_id)
    if post.message_id:
        await call.bot.delete_message(
            chat_id=config.misc.post_channel_chat_id, message_id=post.message_id
        )
    if post.reserv_message_id:
        await call.bot.delete_message(
            chat_id=config.misc.reserv_channel_id, message_id=post.reserv_message_id
        )
    if post.admin_message_id:
        await call.bot.delete_message(
            chat_id=config.misc.admin_channel_id, message_id=post.admin_message_id
        )
    await call.bot.send_message(
        post.user_id, f'Ваш пост {post.title}{hide_link(post.media_url)} було видалено адміністратором')
    await call.message.answer('Пост було видалено')
    await call.message.delete()
    await deal_db.delete_deal(post.deal_id)
    await post_db.delete_post(post_id)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        moderate_main_page, IsAdminFilter(), manage_post_cb.filter(action='back'), state='*')
    dp.register_callback_query_handler(
        confirm_delete_post, IsAdminFilter(), manage_post_cb.filter(action='delete'), state='*')
    dp.register_callback_query_handler(
        close_edit_post, IsAdminFilter(), manage_post_cb.filter(action='close'), state='*')

    dp.register_callback_query_handler(
        delete_post_cmd, IsAdminFilter(), manage_post_cb.filter(action='conf_delete_post'), state='*')