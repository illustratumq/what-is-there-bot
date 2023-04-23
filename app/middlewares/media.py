import asyncio
from typing import Any

from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message


class MediaMiddleware(BaseMiddleware):
    media: dict = {}

    def __init__(self, latency: int | float = 0.001):
        self.latency = latency
        super().__init__()

    async def on_process_message(self, msg: Message, data: dict):
        if not msg.media_group_id:
            return
        try:
            self.media[msg.media_group_id].append(msg)
            raise CancelHandler()
        except KeyError:
            self.media[msg.media_group_id] = [msg]
            await asyncio.sleep(self.latency)

            msg.conf['is_last'] = True
            data['media'] = self.media[msg.media_group_id]

    async def on_post_process_message(self, msg: Message, *args: Any, **kwargs: Any):
        if msg.media_group_id and msg.conf.get('is_last'):
            del self.media[msg.media_group_id]
