from aiogram import Dispatcher
from aiogram.types import CallbackQuery

from app.config import Config
from app.database.services.enums import DealStatusEnum
from app.database.services.repos import PostRepo, RoomRepo, DealRepo
from app.filters import IsAdminFilter
from app.keyboards.inline.admin import manage_post_cb
from app.keyboards.inline.chat import confirm_moderate_kb


async def delete_post_cmd(call: CallbackQuery, callback_data: dict, post_db: PostRepo,
                          deal_db: DealRepo, room_db: RoomRepo, config: Config):
    post_id = int(callback_data['post_id'])
    post = await post_db.get_post(post_id)
    deal = await deal_db.get_deal_post(post_id)
    room = await room_db.get_room(deal.chat_id)
    if post.status == DealStatusEnum.BUSY:
        await call.message.edit_text(
            f'Цей пост вже зайнятий в {room.name}, все одно видалити пост?',
            reply_markup=confirm_moderate_kb(deal, action='delete_post')
        )
    else:
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
        await call.bot.send_message(post.user_id, f'Ваш пост {post.title} було видалено адміністратором')
        await call.message.answer('Пост було видалено')
        await deal_db.delete_deal(post.deal_id)
        await post_db.delete_post(post_id)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(delete_post_cmd, IsAdminFilter(), manage_post_cb.filter(action='delete'), state='*')