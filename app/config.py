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
    fondy_secret_key_1: str
    fondy_secret_key_2: str
    fondy_secret_key_3: str
    fondy_merchant_id_1: str
    fondy_merchant_id_2: str
    fondy_merchant_id_3: str


@dataclass
class UserBot:
    api_id: str
    api_hash: str
    session_name: str


@dataclass
class Miscellaneous:
    log_level: int
    media_channel_chat_id: int
    post_channel_chat_id: int
    admin_help_channel_id: int
    admin_channel_id: int
    reserv_channel_id: int
    database_channel_id: int
    history_channel_id: int
    chat_activity_period: int
    timezone: str

@dataclass
class Django:
    server_host_ip: int
    django_site_port: int
    login: str
    password: str

    @property
    def base_link(self):
        return f'http://{self.server_host_ip}:{self.django_site_port}/admin/'

    def model_link(self, name: str, model_id: int):
        return self.base_link + '/'.join([
            'whatistherebot', name, str(model_id), 'change'
        ])

@dataclass
class Config:
    bot: TgBot
    db: DbConfig
    redis: RedisConfig
    misc: Miscellaneous
    userbot: UserBot
    django: Django

    @classmethod
    def from_env(cls, path: str = None) -> 'Config':
        env = Env()
        env.read_env(path)

        return Config(
            bot=TgBot(
                token=env.str('BOT_TOKEN'),
                admin_ids=tuple(map(int, env.list('ADMIN_IDS'))),
                moder_ids=tuple(map(int, env.list('MODER_IDS'))),
                fondy_secret_key_1=env.str('FONDY_SECRET_KEY_1'),
                fondy_secret_key_2=env.str('FONDY_SECRET_KEY_2'),
                fondy_secret_key_3=env.str('FONDY_SECRET_KEY_3'),
                fondy_merchant_id_1=env.int('FONDY_MERCHANT_ID_1'),
                fondy_merchant_id_2=env.int('FONDY_MERCHANT_ID_2'),
                fondy_merchant_id_3=env.int('FONDY_MERCHANT_ID_3'),
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
                admin_channel_id=env.int('ADMIN_CHANNEL_ID'),
                admin_help_channel_id=env.int('ADMIN_HELP_CHANNEL_ID'),
                reserv_channel_id=env.int('RESERV_CHANNEL_ID'),
                timezone=env.str('TIMEZONE'),
                database_channel_id=env.str('DATABASE_CHANNEL_ID'),
                chat_activity_period=env.int('CHAT_ACTIVITY_PERIOD'),
                history_channel_id=env.int('HISTORY_CHANNEL_ID')
            ),
            userbot=UserBot(
                api_id=env.str('USERBOT_API_ID', None),
                api_hash=env.str('USERBOT_API_HASH', None),
                session_name=env.str('USERBOT_SESSION_NAME', 'userbot'),
            ),
            django=Django(
                server_host_ip=env.str('SERVER_HOST_ID', '127.0.0.1'),
                django_site_port=env.str('DJANGO_SITE_PORT', '8000'),
                login=env.str('DJANGO_SUPERUSER_USERNAME'),
                password=env.str('DJANGO_SUPERUSER_PASSWORD')
            )
        )
