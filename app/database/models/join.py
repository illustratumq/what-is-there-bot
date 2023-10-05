import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from app.database.models.base import TimedBaseModel
from app.database.services.enums import JoinStatusEnum


class Join(TimedBaseModel):
    join_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    post_id = sa.Column(sa.BIGINT, sa.ForeignKey('posts.post_id', ondelete='SET NULL'), nullable=False)
    deal_id = sa.Column(sa.BIGINT, nullable=True, index=True)

    customer_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False)
    executor_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False)

    post_msg_id = sa.Column(sa.BIGINT, nullable=True)
    join_msg_id = sa.Column(sa.BIGINT, nullable=True)

    comment = sa.Column(sa.VARCHAR(500), nullable=True)
    status = sa.Column(ENUM(JoinStatusEnum), nullable=False, default=JoinStatusEnum.EDIT)
    one_time_join = sa.Column(sa.BOOLEAN, nullable=False, default=False)