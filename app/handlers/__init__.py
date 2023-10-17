import logging

from aiogram import Dispatcher

from app.handlers import error, group, private, admin
from app.handlers.private import non_state_message

log = logging.getLogger(__name__)


def setup(dp: Dispatcher):
    error.setup(dp)
    admin.setup(dp)
    private.setup(dp)
    group.setup(dp)
    # non_state_message.setup(dp)
    log.info('Хендлери встановлені...')
