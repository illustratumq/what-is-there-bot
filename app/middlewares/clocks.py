from aiogram.dispatcher.handler import current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import CallbackQuery, Message, User


class ClocksMiddleware(BaseMiddleware):
    allowed_updates = ['message', 'callback_query']

    @staticmethod
    async def setup_chat(user: User):
        await user.bot.send_chat_action(user.id, 'typing')

    async def on_process_message(self, message: Message, data: dict):
        handler = current_handler.get()
        if hasattr(handler, 'clocks'):
            await self.setup_chat(message.from_user)

    async def on_process_callback_query(self, call: CallbackQuery, data: dict):
        handler = current_handler.get()
        if hasattr(handler, 'clocks'):
            await self.setup_chat(call.from_user)

    @staticmethod
    async def on_post_process_callback_query(call: CallbackQuery, args: list, data: dict):
        handler = current_handler.get()
        if not hasattr(handler, 'is_answered'):
            await call.answer()
