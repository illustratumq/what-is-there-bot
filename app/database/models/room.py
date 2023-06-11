import os

import sqlalchemy as sa
from aiogram.types import InputFile
from aiogram.utils.markdown import hide_link
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import RoomStatusEnum
from app.misc.media_template import make_admin_media_template


class Room(TimedBaseModel):
    chat_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False)
    name = sa.Column(sa.VARCHAR(150), nullable=True)
    invite_link = sa.Column(sa.VARCHAR(150), unique=True, nullable=False)
    status = sa.Column(ENUM(RoomStatusEnum), default=RoomStatusEnum.AVAILABLE, nullable=False)
    admin_required = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    admin_id = sa.Column(sa.BIGINT, nullable=True)
    message_id = sa.Column(sa.BIGINT, nullable=True)
    photo_url = sa.Column(sa.VARCHAR(150), nullable=True)
    reason = sa.Column(sa.VARCHAR(150), nullable=True)

    async def construct_admin_moderate_text(self, room_db, bot, config, admin=None, done_action: str = None) -> str:
        if not done_action:
            status = 'Активний' if not admin else f'Модерується {admin.full_name}'
            file = 'need'
        else:
            status = f'{done_action} {admin.full_name}'
            file = 'done'
        admin_msg_photo = make_admin_media_template(self.name, self.reason, status=status, file=file)
        photo_msg = await bot.send_photo(config.misc.media_channel_chat_id, InputFile(admin_msg_photo))
        await room_db.update_room(self.chat_id, photo_url=photo_msg.url)
        os.remove(admin_msg_photo)
        return f'#Виклик_Адміністратора в {self.name}{hide_link(self.photo_url)}\nСтатус: {status}'

    def construct_html_text(self, text: str) -> str:
        return f'<a href="{self.invite_link}">{text}</a>'