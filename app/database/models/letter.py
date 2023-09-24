import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Letter(TimedBaseModel):
    letter_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False)
    join_id = sa.Column(sa.BIGINT, sa.ForeignKey('joins.join_id', ondelete='SET NULL'), nullable=True)
    deal_id = sa.Column(sa.BIGINT, sa.ForeignKey('deals.deal_id', ondelete='SET NULL'), nullable=True)
    post_id = sa.Column(sa.BIGINT, sa.ForeignKey('posts.post_id', ondelete='SET NULL'), nullable=True)

    text = sa.Column(sa.VARCHAR(1500), nullable=False)
    read = sa.Column(sa.BOOLEAN, default=False)
