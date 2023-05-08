from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType

from app.database.services.enums import DealStatusEnum
from app.database.services.repos import DealRepo, PostRepo, RoomRepo
from app.keyboards import Buttons
from app.keyboards.reply.menu import basic_kb


async def my_chats_cmd(msg: Message, deal_db: DealRepo, post_db: PostRepo, room_db: RoomRepo):
    deals_customer = await deal_db.get_deal_customer(msg.from_user.id, DealStatusEnum.BUSY)
    deals_executor = await deal_db.get_deal_executor(msg.from_user.id, DealStatusEnum.BUSY)
    if not deals_customer and not deals_executor:
        await msg.answer('У вас немає активних чатів')
        return

    text = '💬 Ваші активні чати\n\n'
    counter = 1

    for deal in deals_customer:
        if deal.status == DealStatusEnum.BUSY and deal.chat_id:
            post = await post_db.get_post(deal.post_id)
            room = await room_db.get_room(deal.chat_id)
            text += f'{counter}. 🔗 {room.invite_link} "{post.title}" (Ви замовник)\n'
            counter += 1

    for deal in deals_executor:
        if deal.status == DealStatusEnum.BUSY and deal.chat_id:
            post = await post_db.get_post(deal.post_id)
            room = await room_db.get_room(deal.chat_id)
            text += f'{counter}. 🔗 {room.invite_link} "{post.title}" (Ви виконавець)\n'
            counter += 1

    await msg.answer(text=text, disable_web_page_preview=True, reply_markup=basic_kb([Buttons.menu.back]))


def setup(dp: Dispatcher):
    dp.register_message_handler(my_chats_cmd, ChatTypeFilter(ChatType.PRIVATE), text=Buttons.menu.my_chats, state='*')
