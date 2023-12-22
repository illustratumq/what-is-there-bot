import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Merchant(TimedBaseModel):
    merchant_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False)
    secret_key=sa.Column(sa.VARCHAR, nullable=False)
    percent = sa.Column(sa.FLOAT, nullable=False)
    name = sa.Column(sa.VARCHAR, nullable=False)
