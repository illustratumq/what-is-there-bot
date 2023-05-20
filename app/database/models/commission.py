import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Commission(TimedBaseModel):
    pack_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    commission = sa.Column(sa.INTEGER, nullable=False, default=5)
    trigger = sa.Column(sa.INTEGER, nullable=False, default=200)
    under = sa.Column(sa.INTEGER, nullable=False, default=5)
    minimal = sa.Column(sa.INTEGER, nullable=False, default=30)
    maximal = sa.Column(sa.INTEGER, nullable=False, default=15000)
    name = sa.Column(sa.VARCHAR(255), nullable=True)
    description = sa.Column(sa.VARCHAR(500), nullable=True)

    def calculate_commission(self, need_to_pay: int):
        if need_to_pay <= self.trigger:
            return self.under
        else:
            return round(need_to_pay * self.commission/100)
