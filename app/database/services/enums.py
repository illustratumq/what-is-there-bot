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
    BUSY = '🟠 Виконується'
    DONE = '✅ Виконано'


class RoomStatusEnum(Enum):
    AVAILABLE = 'AVAILABLE'
    BUSY = 'BUSY'


class DealStatusEnum(Enum):
    ACTIVE = 'ACTIVE'
    BUSY = 'BUSY'
    DONE = 'DONE'
    DISABLES = 'DISABLED'
    MODERATE = 'MODERATE'
