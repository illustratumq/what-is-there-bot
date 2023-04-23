import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, ARRAY

from app.database.models.base import TimedBaseModel
from app.database.services.enums import DealStatusEnum


class Deal(TimedBaseModel):
    deal_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    post_id = sa.Column(sa.BIGINT, sa.ForeignKey('posts.post_id', ondelete='SET NULL'), nullable=False)
    chat_id = sa.Column(sa.BIGINT, sa.ForeignKey('rooms.chat_id', ondelete='SET NULL'), nullable=True)
    customer_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False, index=True)
    executor_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)
    willing_ids = sa.Column(ARRAY(sa.BIGINT), default=[], nullable=False, )

    price = sa.Column(sa.INTEGER, default=0, nullable=False)
    payed = sa.Column(sa.INTEGER, default=0, nullable=False)
    status = sa.Column(ENUM(DealStatusEnum), default=DealStatusEnum.MODERATE, nullable=False)
    rating = sa.Column(sa.INTEGER, nullable=True)
    comment = sa.Column(sa.VARCHAR(300), nullable=True)

    @property
    def participants(self):
        return [self.executor_id, self.customer_id]

    def construct_price(self):
        return f'{self.price} грн' if self.price > 0 else 'Договірна'

    def chat_status(self):
        if self.payed >= self.price and self.payed > 0:
            return 'Оплачена'
        else:
            return 'Неоплачена'
