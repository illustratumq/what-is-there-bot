import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Setting(TimedBaseModel):
    user_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False, nullable=False)
    can_be_customer = sa.Column(sa.BOOLEAN(), nullable=False, default=True)
    can_be_executor = sa.Column(sa.BOOLEAN(), nullable=False, default=True)
    can_publish_post = sa.Column(sa.BOOLEAN(), nullable=False, default=True)
    need_check_post = sa.Column(sa.BOOLEAN(), nullable=False, default=True)

    @staticmethod
    def format(text: str, value: bool) -> str:
        return f'{text}: {"✔" if value else "Вимк."}'
