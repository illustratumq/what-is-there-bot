from aiogram import Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import Message, ChatType


async def non_state_message_cmd(msg: Message):
    await msg.answer(
        'Наш бот запрограмований на керування кнопками, текстові '
        'повідомлення не оброблюються. Щоб повернутись в головне меню натисніть /menu'
    )


def setup(dp: Dispatcher):
    dp.register_message_handler(non_state_message_cmd, ChatTypeFilter(ChatType.PRIVATE))
