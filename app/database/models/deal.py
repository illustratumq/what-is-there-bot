import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, ARRAY

from app.config import Config
from app.database.models.base import TimedBaseModel
from app.database.services.enums import DealStatusEnum, DealTypeEnum
from app.misc.times import now


class Deal(TimedBaseModel):
    deal_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    post_id = sa.Column(sa.BIGINT, sa.ForeignKey('posts.post_id', ondelete='SET NULL'), nullable=True)
    chat_id = sa.Column(sa.BIGINT, sa.ForeignKey('rooms.chat_id', ondelete='SET NULL'), nullable=True)
    customer_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)
    executor_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)

    price = sa.Column(sa.INTEGER, default=0, nullable=False)
    payed = sa.Column(sa.INTEGER, default=0, nullable=False)
    status = sa.Column(ENUM(DealStatusEnum), default=DealStatusEnum.MODERATE, nullable=False)
    type = sa.Column(ENUM(DealTypeEnum), default=DealTypeEnum.PUBLIC, nullable=False)
    rating = sa.Column(sa.INTEGER, nullable=True)
    comment = sa.Column(sa.VARCHAR(500), nullable=True)

    no_media = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    next_activity_date = sa.Column(sa.DateTime, nullable=True)
    activity_confirm = sa.Column(sa.BOOLEAN, default=True, nullable=False)
    log = sa.Column(sa.VARCHAR, nullable=True)

    @property
    def participants(self):
        return [self.executor_id, self.customer_id]

    @property
    def deal_price(self):
        return f'{self.price} грн' if self.price > 0 else 'Договірна'

    @property
    def chat_status(self):
        if self.payed >= self.price and self.payed > 0:
            return 'Оплачена'
        elif self.price > self.payed and self.price > 0:
            return 'Не доплачена'
        else:
            return 'Неоплачена'

    async def create_log(self, deal_db, text: str):
        log = self.log if self.log else ''
        new_log = log + f'\n[{now().strftime("%H:%M:%S %d.%m.%y")}]: {text}'
        await deal_db.update_deal(self.deal_id, log=new_log)

    @property
    def server_url(self):
        config = Config.from_env()
        return config.django.model_link('deal', self.deal_id)
