import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import OrderStatusEnum, OrderTypeEnum


class Order(TimedBaseModel):
    id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    deal_id = sa.Column(sa.BIGINT, sa.ForeignKey('deals.deal_id', ondelete='SET NULL'), nullable=False)
    merchant_id = sa.Column(sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)
    url = sa.Column(sa.VARCHAR, nullable=True)
    request_body = sa.Column(sa.JSON, default={}, nullable=False)
    request_answer = sa.Column(sa.JSON, default={}, nullable=True)
    request_reverse = sa.Column(sa.JSON, default={}, nullable=True)
    log = sa.Column(sa.VARCHAR, nullable=True)

    @property
    def order_id(self) -> str:
        return str(int(self.created_at.timestamp()) + self.deal_id * self.id * int(self.created_at.microsecond / 10e3))

