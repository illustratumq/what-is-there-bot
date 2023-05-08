from datetime import timedelta, datetime

from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import CallbackQuery, ChatActions, ChatType

from app.config import Config
from app.database.services.enums import DealStatusEnum, RoomStatusEnum
from app.database.services.repos import DealRepo, PostRepo, UserRepo, RoomRepo
from app.handlers.userbot import UserbotController
from app.keyboards.inline.deal import deal_cb, join_room_kb
from app.misc.commands import set_new_room_commands
from app.misc.times import now


async def create_room_cmd(call: CallbackQuery, callback_data: dict, deal_db: DealRepo,
                          post_db: PostRepo, room_db: RoomRepo, user_db: UserRepo, config: Config,
                          userbot: UserbotController):
    await call.message.delete_reply_markup()
    deal_id = int(callback_data['deal_id'])
    executor_id = int(callback_data['executor_id'])
    deal = await deal_db.get_deal(deal_id)

    if deal.status == DealStatusEnum.BUSY:
        await call.answer('Ви не можете зв\'язатись з ще одним виконавцем', show_alert=True)
        return

    await deal_db.update_deal(deal_id, status=DealStatusEnum.BUSY)
    await post_db.update_post(deal.post_id, status=DealStatusEnum.BUSY)

    post = await post_db.get_post(deal.post_id)
    if post.message_id:
        await call.bot.edit_message_text(
            chat_id=config.misc.post_channel_chat_id, message_id=post.message_id,
            text=post.construct_post_text()
        )
    await call.bot.edit_message_text(
        chat_id=config.misc.reserv_channel_id, message_id=post.reserv_message_id,
        text=post.construct_post_text()
    )
    room_chat_id, invite_link = await get_room(call, room_db, userbot)
    await deal_db.update_deal(
        deal_id, chat_id=room_chat_id, executor_id=executor_id,
        next_activity_date=datetime.now() + timedelta(minutes=1)
    )
    text = (
        f'Угода ухвалена. Заходьте до кімнати замовлення "{post.title}" за цим посиланням:\n\n'
        f'{invite_link}\n\nАбо натисніть на кнопку під цим повідомленням'
    )
    await call.bot.send_message(
        deal.customer_id, text=text, reply_markup=join_room_kb(invite_link), disable_web_page_preview=True)
    await call.bot.send_message(
        executor_id, text=text, reply_markup=join_room_kb(invite_link), disable_web_page_preview=True)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(
        create_room_cmd, ChatTypeFilter(ChatType.PRIVATE), deal_cb.filter(action='chat'), state='*')


async def get_room(call: CallbackQuery, room_db: RoomRepo, userbot: UserbotController) -> tuple[int, str]:
    room = await room_db.get_free_room()
    await call.message.answer('Очікуйте, ми створюємо для вас кімнату...')
    if room is None:
        await call.bot.send_chat_action(call.from_user.id, ChatActions.FIND_LOCATION)
        quantity_of_rooms = await room_db.count()
        chat, invite_link = await userbot.create_new_room(quantity_of_rooms)
        await room_db.add(chat_id=chat.id, invite_link=invite_link.invite_link, status=RoomStatusEnum.BUSY)
        await set_new_room_commands(call.bot, chat.id, await userbot.get_client_user_id())
        chat_id = chat.id
        invite_link = invite_link.invite_link
    else:
        await call.bot.send_chat_action(call.from_user.id, ChatActions.FIND_LOCATION)
        await room_db.update_room(room.chat_id, status=RoomStatusEnum.BUSY)
        chat_id = room.chat_id
        invite_link = room.invite_link
    return chat_id, invite_link
