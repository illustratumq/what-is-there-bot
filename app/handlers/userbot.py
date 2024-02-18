import logging
import os
from datetime import timedelta

import pyrogram
from aiogram import Bot
from aiogram.types import ChatPermissions
from pyrogram import Client, raw, utils, types
from pyrogram.errors import ChatIdInvalid
from pyrogram.raw.core import TLObject
from pyrogram.raw.functions.messages import EditChatAdmin, DeleteChat
from pyrogram.raw.types import ChatAdminRights, InputChannel
from pyrogram.types import Chat, ChatInviteLink, ChatMember, Message

from app.config import UserBot
from app.misc.media import make_chat_photo_template
from app.misc.times import now

log = logging.getLogger(__name__)

class UserbotController:
    def __init__(self, config: UserBot, bot_username: str, chat_photo_path: str):
        try:
            self._client = Client(config.session_name, no_updates=True)
        except:
            self._client = Client(config.session_name, config.api_id, config.api_hash, no_updates=True)
        self._bot_username = bot_username
        self._chat_photo_path = chat_photo_path

    async def connect(self):
        try:
            await self._client.connect()
            self._client.me = await self._client.get_me()
        except Exception as Error:
            # log.warning(Error)
            pass

    async def get_client_user_id(self) -> int:
        await self.connect()
        user_id = (await self._client.get_me()).id
        return user_id

    async def get_chat_members(self, chat_id: int) -> list:
        members = []
        await self.connect()
        try:
            async for member in self._client.get_chat_members(chat_id):
                member: ChatMember
                members.append(member.user.id)
        except:
            pass
        return members

    async def get_chat_history(self, chat_id: int) -> list[Message]:
        await self.connect()
        client = self._client
        history = client.get_chat_history(chat_id=chat_id)
        messages = []
        async for msg in history:
            messages.append(msg)
        return messages[::-1]

    async def create_new_room(self, last_room_number: int) -> tuple[Chat, ChatInviteLink, str]:
        """
        :param last_room_number: room_id of last created room
        :return: chat, invite_link, room_name
        """
        await self.connect()
        client = self._client
        chat, room_name = await self._create_group(client, last_room_number)
        await self._set_chat_photo(chat, last_room_number)
        await self._set_chat_permissions(client, chat)
        await self._set_bot_admin(client, chat)
        invite_link = await self._create_invite_link(client, chat)
        return chat, invite_link, room_name

    async def _create_group(self, client: Client, last_room_number: int) -> tuple[Chat, str]:
        await self.connect()
        new_room_number = last_room_number + 1
        name = f'Чат №{new_room_number}'
        group = await client.create_group(name, [self._bot_username])
        return group, name

    @staticmethod
    async def _set_chat_permissions(client: Client, chat: Chat) -> None:
        permissions = ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True,
            can_send_polls=False, can_add_web_page_previews=False, can_change_info=False,
            can_invite_users=False, can_pin_messages=True,
        )
        await client.set_chat_permissions(chat.id, permissions)

    async def _set_chat_photo(self, chat: Chat, last_room_number: int) -> None:
        new_photo_path = make_chat_photo_template(self._chat_photo_path, last_room_number + 1)
        await chat.set_photo(photo=new_photo_path)
        os.remove(new_photo_path)

    @staticmethod
    async def _create_invite_link(client: Client, chat: Chat) -> ChatInviteLink:
        return await client.create_chat_invite_link(chat.id, name='For join requests', creates_join_request=True)

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

    async def add_chat_member(self, chat_id: int, user_id: int):
        await self.connect()
        client = self._client
        await client.add_chat_members(chat_id=chat_id, user_ids=user_id)

    async def kick_chat_member(self, chat_id: int, user_id: int):
        await self.connect()
        until_date = now() + timedelta(seconds=300)
        await self._client.ban_chat_member(chat_id=chat_id, user_id=user_id, until_date=until_date)

    async def delete_chat_history(self, chat_id: int):
        for message in await self.get_chat_history(chat_id):
            try:
                await self._client.delete_messages(chat_id, message.id)
            except:
                pass

    async def create_chat_link(self, chat_id: int):
        return await self._client.create_chat_invite_link(chat_id, name='New chat link')

    async def delete_group(self, chat_id: int) -> None:
        await self.connect()
        client = self._client
        raw = DeleteChat(chat_id=chat_id)
        try:
            await self._invoke(client, raw)
        except ChatIdInvalid:
            raw.chat_id = -chat_id
            await self._invoke(client, raw)
