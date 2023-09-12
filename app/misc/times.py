from datetime import datetime, timedelta

import pytz

from app.config import Config

config = Config.from_env()


def now():
    return datetime.now().astimezone(pytz.timezone(config.misc.timezone))


def deltatime(date: str):
    if '-' in date:
        return [
            datetime.strptime(date.split('-')[0], '%d.%m.%y'),
            datetime.strptime(date.split('-')[-1], '%d.%m.%y')
        ]
    elif date == 'week':
        end = now().replace(hour=23, minute=59, second=59)
        start = (end - timedelta(days=7)).replace(minute=0, hour=0, second=1)
        return start, end
    elif date == 'month':
        end = now().replace(hour=23, minute=59, second=59)
        start = now().replace(day=1, hour=0, minute=0, second=1)
        return start, end
    elif date == 'today':
        return datetime.now().replace(hour=0, minute=0, second=1)
    else:
        return datetime.strptime(date, '%d.%m.%y').replace(hour=0, minute=0, second=1)

def next_run_time(seconds: int = 5*60):
    return now() + timedelta(seconds=seconds)


def localize(date: datetime):
    return date.astimezone(pytz.timezone(config.misc.timezone))