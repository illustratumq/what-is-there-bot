import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import RoomStatusEnum


class Room(TimedBaseModel):
    chat_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False)
    name = sa.Column(sa.VARCHAR(150), nullable=True)
    invite_link = sa.Column(sa.VARCHAR(150), unique=True, nullable=False)
    status = sa.Column(ENUM(RoomStatusEnum), default=RoomStatusEnum.AVAILABLE, nullable=False)
    admin_required = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    admin_id = sa.Column(sa.BIGINT, nullable=True)
    message_id = sa.Column(sa.BIGINT, nullable=True)

    def construct_admin_moderate_text(self) -> str:
        return (
            f'Потрбіна модерація в чаті: "{self.name}"\n\n'
            f'⚒ #Виклик_Адміністратора'
        )

    def construct_html_text(self, text: str) -> str:
        return f'<a href="{self.invite_link}">{text}</a>'
