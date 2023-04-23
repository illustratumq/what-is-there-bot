from datetime import datetime, timedelta

import pytz

from app.config import Config

config = Config.from_env()


def now():
    return datetime.now().astimezone(pytz.timezone(config.misc.timezone))


def next_run_time(seconds: int = 5*60):
    return now() + timedelta(seconds=seconds)


def localize(date: datetime):
    return date.astimezone(pytz.timezone(config.misc.timezone))