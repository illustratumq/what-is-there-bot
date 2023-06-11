import logging
from dataclasses import dataclass

from environs import Env
from sqlalchemy.engine import URL


@dataclass
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    reset_db: bool

    @property
    def sqlalchemy_url(self) -> URL:
        return URL.create(
            'postgresql+asyncpg',
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )


@dataclass
class RedisConfig:
    host: str
    port: int


@dataclass
class TgBot:
    token: str
    admin_ids: tuple[int]
    moder_ids: tuple[int]
    bot_link: str
    payment_token: str
    fondy_credit_key: str
    fondy_merchant_id: str


@dataclass
class UserBot:
    api_id: str
    api_hash: str
    session_name: str


@dataclass
class Miscellaneous:
    log_level: int
    server_host_ip: str
    media_channel_chat_id: int
    post_channel_chat_id: int
    admin_channel_id: int
    reserv_channel_id: int
    update_commands: bool
    timezone: str


@dataclass
class Config:
    bot: TgBot
    db: DbConfig
    redis: RedisConfig
    misc: Miscellaneous
    userbot: UserBot

    @classmethod
    def from_env(cls, path: str = None) -> 'Config':
        env = Env()
        env.read_env(path)

        return Config(
            bot=TgBot(
                token=env.str('BOT_TOKEN'),
                admin_ids=tuple(map(int, env.list('ADMIN_IDS'))),
                moder_ids=tuple(map(int, env.list('MODER_IDS'))),
                payment_token=env.str('PAYMENT_TOKEN'),
                fondy_credit_key=env.str('FONDY_CREDIT_KEY'),
                fondy_merchant_id=env.str('FONDY_MERCHANT_ID'),
                bot_link=env.str('BOT_LINK')
            ),
            db=DbConfig(
                host=env.str('DB_HOST', 'localhost'),
                port=env.int('DB_PORT', 5432),
                user=env.str('DB_USER', 'postgres'),
                password=env.str('DB_PASS', 'postgres'),
                database=env.str('DB_NAME', 'postgres'),
                reset_db=env.bool('RESET_DB', False)
            ),
            redis=RedisConfig(
                host=env.str('REDIS_HOST', 'localhost'),
                port=env.int('REDIS_PORT', 6379),
            ),
            misc=Miscellaneous(
                log_level=env.log_level('LOG_LEVEL', logging.INFO),
                media_channel_chat_id=env.int('MEDIA_CHANNEL_CHAT_ID'),
                post_channel_chat_id=env.int('POST_CHANNEL_CHAT_ID'),
                update_commands=env.bool('UPDATE_COMMANDS', True),
                admin_channel_id=env.int('ADMIN_CHANNEL_ID'),
                reserv_channel_id=env.int('RESERV_CHANNEL_ID'),
                timezone=env.str('TIMEZONE'),
                server_host_ip=env.str('SERVER_HOST_IP')
            ),
            userbot=UserBot(
                api_id=env.str('USERBOT_API_ID', None),
                api_hash=env.str('USERBOT_API_HASH', None),
                session_name=env.str('USERBOT_SESSION_NAME', 'userbot'),
            )
        )
