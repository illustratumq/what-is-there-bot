import sqlalchemy as sa

from app.database.models.base import TimedBaseModel


class Marker(TimedBaseModel):
    user_id = sa.Column(sa.BIGINT, sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=False, index=True)
    marker_id = sa.Column(sa.BIGINT, primary_key=True, autoincrement=True)
    text = sa.Column(sa.VARCHAR(20), nullable=False)
