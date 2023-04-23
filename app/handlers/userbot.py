from pyrogram import Client
from pyrogram.errors import ChatIdInvalid
from pyrogram.raw.core import TLObject
from pyrogram.raw.functions.messages import EditChatAdmin, DeleteChat
from pyrogram.types import Chat, ChatInviteLink, ChatPermissions

from app.config import UserBot


class UserbotController:
    def __init__(self, config: UserBot, bot_username: str, chat_photo_path: str):
        try:
            self._client = Client(config.session_name, no_updates=True)
        except AttributeError:
            self._client = Client(config.session_name, config.api_id, config.api_hash, no_updates=True)
        self._bot_username = bot_username
        self._chat_photo_path = chat_photo_path

    async def get_client_user_id(self) -> int:
        async with self._client:
            return (await self._client.get_me()).id

    async def clean_chat_history(self, chat_id: int):
        async with self._client as Client:
            history = Client.get_chat_history(chat_id=chat_id)
            message_ids = []
            async for msg in history:
                message_ids.append(msg.id)
            await Client.delete_messages(chat_id=chat_id, message_ids=message_ids)

    async def create_new_room(self, last_room_number: int) -> tuple[Chat, ChatInviteLink]:
        async with self._client as client:
            chat = await self._create_group(client, last_room_number)
            await self._set_chat_photo(chat)
            await self._set_chat_permissions(client, chat)
            await self._set_bot_admin(client, chat)
            invite_link = await self._create_invite_link(client, chat)
        return chat, invite_link

    async def _create_group(self, client: Client, last_room_number: int) -> Chat:
        new_room_number = last_room_number + 1
        group = await client.create_group(f'Чат №{new_room_number}', [self._bot_username])
        return group

    @staticmethod
    async def _set_chat_permissions(client: Client, chat: Chat) -> None:
        permissions = ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True,
            can_send_polls=False, can_add_web_page_previews=False, can_change_info=False,
            can_invite_users=False, can_pin_messages=True,
        )
        await client.set_chat_permissions(chat.id, permissions)

    async def _set_chat_photo(self, chat: Chat) -> None:
        await chat.set_photo(photo=self._chat_photo_path)

    @staticmethod
    async def _create_invite_link(client: Client, chat: Chat) -> ChatInviteLink:
        return await client.create_chat_invite_link(
            chat.id, name='For join requests', expire_date=None, creates_join_request=True
        )

    @staticmethod
    async def _invoke(client: Client, raw_function: TLObject) -> None:
        await client.invoke(raw_function)

    async def _set_bot_admin(self, client: Client, chat: Chat) -> None:
        raw = EditChatAdmin(chat_id=chat.id, user_id=await client.resolve_peer(self._bot_username), is_admin=True)
        try:
            await self._invoke(client, raw)
        except ChatIdInvalid:
            raw.chat_id = -chat.id
            await self._invoke(client, raw)

    async def _delete_group(self, client: Client, chat: Chat) -> None:
        raw = DeleteChat(chat_id=chat.id)
        try:
            await self._invoke(client, raw)
        except ChatIdInvalid:
            raw.chat_id = -chat.id
            await self._invoke(client, raw)
