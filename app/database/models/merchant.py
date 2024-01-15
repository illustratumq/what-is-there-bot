import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Merchant(TimedBaseModel):
    merchant_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False)
    secret_key = sa.Column(sa.VARCHAR, nullable=False)
    p2p_key = sa.Column(sa.VARCHAR, nullable=False)
    percent = sa.Column(sa.FLOAT, nullable=False)
    name = sa.Column(sa.VARCHAR, nullable=False)

    def calculate_commission(self, need_to_pay: int, return_full_price: bool = True) -> float:
        commission = round(need_to_pay / (1 - self.percent), 2)
        if return_full_price:
            return commission
        else:
            return commission - need_to_pay
