import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Commission(TimedBaseModel):
    commission_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    minimal = sa.Column(sa.INTEGER, nullable=False, default=30)
    maximal = sa.Column(sa.INTEGER, nullable=False, default=15000)
    name = sa.Column(sa.VARCHAR(255), nullable=True)
    description = sa.Column(sa.VARCHAR(500), nullable=True)
    trigger_price_1 = sa.Column(sa.INTEGER, default=99, nullable=False)
    trigger_price_2 = sa.Column(sa.INTEGER, default=200, nullable=False)
    merchant_1 = sa.Column(
        sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)
    merchant_2 = sa.Column(
        sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)
    merchant_3 = sa.Column(
        sa.BIGINT, sa.ForeignKey('merchants.merchant_id', ondelete='SET NULL'), nullable=False)

    def choose_merchant(self, need_to_pay: int):
        if need_to_pay <= self.trigger_price_1:
            return self.merchant_3
        elif self.trigger_price_1 < need_to_pay <= self.trigger_price_2:
            return self.merchant_2
        else:
            return self.merchant_1

