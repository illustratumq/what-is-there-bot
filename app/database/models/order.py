import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import OrderStatusEnum, OrderTypeEnum


class Order(TimedBaseModel):
    id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    deal_id = sa.Column(sa.BIGINT, sa.ForeignKey('deals.deal_id', ondelete='SET NULL'), nullable=False)
    price = sa.Column(sa.INTEGER, default=0, nullable=False)
    url = sa.Column(sa.VARCHAR, nullable=True)
    status = sa.Column(ENUM(OrderStatusEnum), default=OrderStatusEnum.CREATED, nullable=False)
    type = sa.Column(ENUM(OrderTypeEnum), default=OrderTypeEnum.ORDER, nullable=False)
    body = sa.Column(sa.JSON, default={}, nullable=False)

    @property
    def order_id(self) -> str:
        return str(int(self.created_at.timestamp()) + self.deal_id * int(self.created_at.microsecond / 10e3))
