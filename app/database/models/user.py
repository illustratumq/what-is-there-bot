import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import UserStatusEnum, UserTypeEnum


class User(TimedBaseModel):
    user_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=False, index=True)
    full_name = sa.Column(sa.VARCHAR(255), nullable=False)
    mention = sa.Column(sa.VARCHAR(300), nullable=False)
    status = sa.Column(ENUM(UserStatusEnum), default=UserStatusEnum.ACTIVE, nullable=False)
    type = sa.Column(ENUM(UserTypeEnum), default=UserTypeEnum.USER, nullable=False)
    balance = sa.Column(sa.BIGINT, default=0, nullable=False)
    description = sa.Column(sa.VARCHAR(500), nullable=True)
    ban_comment = sa.Column(sa.VARCHAR(500), nullable=True)

    async def construct_preview_text(self, deal_db):
        rating, evaluated, deals = await deal_db.calculate_user_rating(self.user_id)
        text = (
            f'📬 Користувач {self.full_name} подав запит на виконання '
            f'вашого завдання\n\n'
            f'Рейтинг: {rating} {self.emojize_rating_text(rating)}\n'
            f'Кількість виконаних угод: {deals}\n'
            f'Кількість оцінених угод: {evaluated}'
        )
        if self.description:
            text += f'\nПро себе: {self.description if self.description else "Немає опису"}'
        return text

    async def construct_my_rating(self, deal_db):
        rating, evaluated, deals = await deal_db.calculate_user_rating(self.user_id)
        text = (
            f'Ваш рейтинг: {rating} {self.emojize_rating_text(rating)}\n'
            f'Кількість ваших виконаних угод: {deals}\n'
            f'Кількість угод які оцінили: {evaluated}\n'
            f'Про себе: {self.description if self.description else "Немає опису"}\n\n'
            f'ℹ Рейтинг рахується тільки для оцінених угод. Неоцінені угоди не впливають на рейтинг.\n\n'
        )
        if not self.description:
            text += (
                'Ви також можете додати короткий опис в розділі "Про себе", який замовник побачить '
                'у вашому запиті на виконання завдання.'
            )
        return text

    @staticmethod
    def emojize_rating_text(rating: int) -> str:
        return '⭐' * int(rating)

    def create_html_link(self, text: str):
        return f'<a href="tg://user?id={self.user_id}">{text}</a>'
