from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.keyboards import Buttons


class IsAdminFilter(BoundFilter):
    async def check(self, upd: Message | CallbackQuery, *args: ...) -> bool:
        data: dict = ctx_data.get()
        config: Config = data['config']
        return upd.from_user.id in config.bot.admin_ids or upd.from_user.id in config.bot.moder_ids


class LetterFilter(BoundFilter):
    async def check(self, msg: Message, *args: ...) -> bool:
        return 'Повідомлення 📩 (' in msg.text
