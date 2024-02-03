import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import OrderTypeEnum


class Order(TimedBaseModel):
    id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    type = sa.Column(ENUM(OrderTypeEnum), default=OrderTypeEnum.ORDER, nullable=False)
    deal_id = sa.Column(sa.BIGINT, sa.ForeignKey('deals.deal_id', ondelete='SET NULL'), nullable=False)
    merchant_id = sa.Column(sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)
    url = sa.Column(sa.VARCHAR, nullable=True)
    request_body = sa.Column(sa.JSON, default={}, nullable=False)
    request_answer = sa.Column(sa.JSON, default={}, nullable=True)
    log = sa.Column(sa.VARCHAR, nullable=True)
    payed = sa.Column(sa.BOOLEAN, nullable=False, default=False)

    @property
    def order_id(self) -> str:
        return str(int(self.created_at.timestamp()) + self.deal_id * self.id * int(self.created_at.microsecond / 10e3))

    def calculate_payout(self):
        actual_amount = int(self.request_answer['response']['actual_amount'])
        amount = int(self.request_answer['response']['amount'])
        commission_for_executor = round((actual_amount - amount), 2)
        return round(amount - commission_for_executor, 2)

    def is_valid_response(self):
        return 'error_message' not in self.request_answer['response'].keys()

    def is_order_status(self, status: str):
        return self.request_answer['response']['order_status'] == status

    @property
    def get_request_body(self):
        return self.request_body['request']
