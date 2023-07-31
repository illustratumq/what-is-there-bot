import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import OrderStatusEnum


class Order(TimedBaseModel):
    id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    deal_id = sa.Column(sa.BIGINT, sa.ForeignKey('deals.deal_id', ondelete='SET NULL'), nullable=False)
    price = sa.Column(sa.INTEGER, default=0, nullable=False)
    url = sa.Column(sa.VARCHAR, nullable=True)
    status = sa.Column(ENUM(OrderStatusEnum), default=OrderStatusEnum.CREATED, nullable=False)

    @property
    def order_id(self):
        return 'order_' + str(self.id) + f'_{self.deal_id}' + '_v1'
