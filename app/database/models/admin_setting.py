import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class AdminSetting(TimedBaseModel):
    setting_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True, nullable=False)
    setting_name = sa.Column(sa.VARCHAR, nullable=False)
    setting_status = sa.Column(sa.BOOLEAN, default=False, nullable=False)
    setting_data = sa.Column(sa.JSON, nullable=True)

    def status(self) -> str:
        return f'{self.setting_name}: {"✔" if self.setting_status else "Вимк."}'
