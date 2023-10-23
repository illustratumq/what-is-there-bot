import os
from datetime import timedelta

from pyrogram import Client
from pyrogram.errors import ChatIdInvalid
from pyrogram.raw.core import TLObject
from pyrogram.raw.functions.messages import EditChatAdmin, DeleteChat
from pyrogram.raw.types import ChatAdminRights
from pyrogram.types import Chat, ChatInviteLink, ChatPermissions, ChatMember

from app.config import UserBot
from app.misc.media import make_chat_photo_template
from app.misc.times import now


class UserbotController:
    def __init__(self, config: UserBot, bot_username: str, chat_photo_path: str):
        # try:
        self._client = Client(config.session_name, no_updates=True)
        # except AttributeError:
        #     self._client = Client(config.session_name, config.api_id, config.api_hash, no_updates=True)
        self._bot_username = bot_username
        self._chat_photo_path = chat_photo_path

    async def connect(self):
        try:
            await self._client.start()
        except:
            pass

    async def get_client_user_id(self) -> int:
        await self.connect()
        user_id = (await self._client.get_me()).id
        return user_id

    async def get_chat_members(self, chat_id: int) -> list:
        members = []
        await self.connect()
        async for member in self._client.get_chat_members(chat_id):
            member: ChatMember
            members.append(member.user.id)
        return members

    async def create_new_room(self, last_room_number: int) -> tuple[Chat, ChatInviteLink, str]:
        '''
        :param last_room_number: room_id of last created room
        :return: chat, invite_link, room_name
        '''
        await self.connect()
        client = self._client
        chat, room_name = await self._create_group(client, last_room_number)
        await self._set_chat_photo(chat, last_room_number)
        await self._set_chat_permissions(client, chat)
        await self._set_bot_admin(client, chat)
        invite_link = await self._create_invite_link(client, chat)
        return chat, invite_link, room_name

    async def _create_group(self, client: Client, last_room_number: int) -> tuple[Chat, str]:
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

    @staticmethod
    async def _set_chat_photo(chat: Chat, last_room_number: int) -> None:
        new_photo_path = make_chat_photo_template(last_room_number + 1)
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
        # await self.connect()
        client = self._client
        await client.add_chat_members(chat_id=chat_id, user_ids=user_id)
        # async with self._client as client:
        #     client: Client
        #     await client.add_chat_members(chat_id=chat_id, user_ids=user_id)

    async def kick_chat_member(self, chat_id: int, user_id: int):
        await self.connect()
        await self._client.ban_chat_member(chat_id=chat_id, user_id=user_id, until_date=now() + timedelta(seconds=5))

    async def _delete_group(self, client: Client, chat: Chat) -> None:
        raw = DeleteChat(chat_id=chat.id)
        try:
            await self._invoke(client, raw)
        except ChatIdInvalid:
            raw.chat_id = -chat.id
            await self._invoke(client, raw)
