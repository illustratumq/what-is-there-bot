import logging

from aiogram import Dispatcher

from app.handlers import error, group, private, admin

log = logging.getLogger(__name__)


def setup(dp: Dispatcher):
    error.setup(dp)
    admin.setup(dp)
    private.setup(dp)
    group.setup(dp)
    log.info('Хендлери встановлені...')
