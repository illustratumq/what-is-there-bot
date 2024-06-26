import sqlalchemy as sa
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils.markdown import hide_link
from sqlalchemy.dialects.postgresql import ENUM

from app.config import Config
from app.database.models.base import TimedBaseModel
from app.database.services.enums import DealStatusEnum, PostStatusText, DealTypeEnum


class Post(TimedBaseModel):
    post_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False, index=True)
    deal_id = sa.Column(sa.BIGINT, nullable=True, index=True)

    message_id = sa.Column(sa.BIGINT, nullable=True)
    admin_message_id = sa.Column(sa.BIGINT, nullable=True)
    reserv_message_id = sa.Column(sa.BIGINT, nullable=True)
    media_id = sa.Column(sa.BIGINT, nullable=True)

    title = sa.Column(sa.VARCHAR(150), nullable=False)
    about = sa.Column(sa.VARCHAR(800), nullable=False)
    price = sa.Column(sa.INTEGER, nullable=False)

    status = sa.Column(ENUM(DealStatusEnum), default=DealStatusEnum.MODERATE, nullable=False)
    type = sa.Column(ENUM(DealTypeEnum), default=DealTypeEnum.PUBLIC, nullable=False)

    post_url = sa.Column(sa.VARCHAR(150), nullable=True)
    media_url = sa.Column(sa.VARCHAR(150), nullable=True)

    def construct_post_text(self, use_bot_link: bool = True) -> str:
        text = (
            f'{self.post_status}\n\n'
            f'<b>{self.title}</b>\n\n'
            f'{self.about}\n\n'
            f'Ціна: {self.post_price}'
            f'{hide_link(self.media_url)}'
        )
        if use_bot_link:
            text += f'\n\n<a href="https://t.me/ENTERinBOT">Відправити своє завдання</a>'
        return text

    def construct_post_text_shorted(self):
        return (
            f'<b>{self.title}</b>\n\n'
            f'{self.about[:100]}...'
            f'{hide_link(self.media_url)}'
        )

    @property
    def post_status(self) -> str:
        if self.status == DealStatusEnum.ACTIVE:
            return PostStatusText.ACTIVE
        if self.status == DealStatusEnum.MODERATE:
            return PostStatusText.MODERATE
        elif self.status == DealStatusEnum.BUSY:
            return PostStatusText.BUSY
        elif self.status == DealStatusEnum.DONE:
            return PostStatusText.DONE
        elif self.status == DealStatusEnum.WAIT:
            return PostStatusText.WAIT
        else:
            return 'Відхилено'

    @property
    def post_price(self):
        return f'{self.price} грн' if self.price != 0 else 'Договірна'

    @property
    async def participate_link(self):
        return await get_start_link(f'participate-{self.deal_id}')

    @property
    async def manage_link(self):
        return await get_start_link(f'manage_post-{self.deal_id}')

    def construct_html_link(self, text: str):
        return f'<a href="{self.post_url}">{text}</a>'

    @property
    def server_url(self):
        config = Config.from_env()
        return config.django.model_link('post', self.post_id)
