from enum import Enum


class UserStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    BANNED = 'BANNED'

class UserTypeEnum(Enum):
    USER = 'USER'
    MODERATOR = 'MODERATOR'
    ADMIN = 'ADMIN'


class PostStatusText:
    ACTIVE = '⚪ Активно'
    BUSY = '🟡 Виконується'
    DONE = '✅ Виконано'
    MODERATE = '📌 Очікує модерації'
    WAIT = '🕓 Очікує публікації'


class RoomStatusEnum(Enum):
    AVAILABLE = 'AVAILABLE'
    BUSY = 'BUSY'


class DealStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    BUSY = 'BUSY'
    DONE = 'DONE'
    DISABLES = 'DISABLED'
    MODERATE = 'MODERATE'
    WAIT = 'WAIT'


class DealTypeEnum(Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'


class OrderTypeEnum(Enum):
    ORDER = 'ORDER'
    CAPTURE = 'CAPTURE'
    REVERSE = 'REVERSE'
    PAYOUT = 'PAYOUT'

class JoinStatusEnum(Enum):
    EDIT = 'EDIT'
    ACTIVE = 'ACTIVE'
    DISABLE = 'DISABLE'
    USED = 'USED'


