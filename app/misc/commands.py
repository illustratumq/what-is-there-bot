from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeChatMember


async def set_new_room_commands(bot: Bot, chat_id: int, admin_id: int) -> None:
    default_commands = [
        BotCommand('menu', 'Показати меню'),
    ]
    admin_commands = [
        BotCommand('admin', 'Перейти до адмін панелі'),
        *default_commands,
    ]
    await bot.set_my_commands(
        commands=default_commands,
        scope=BotCommandScopeChat(chat_id=chat_id)
    )
    await bot.set_my_commands(
        commands=admin_commands,
        scope=BotCommandScopeChatMember(chat_id=chat_id, user_id=admin_id)
    )
