import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import RoomStatusEnum


class Room(TimedBaseModel):
    chat_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False)
    invite_link = sa.Column(sa.VARCHAR(150), unique=True, nullable=False)
    status = sa.Column(ENUM(RoomStatusEnum), default=RoomStatusEnum.AVAILABLE, nullable=False)
