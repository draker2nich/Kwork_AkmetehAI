import asyncio
import traceback
from collections import defaultdict
from typing import Dict, Any, Callable, Awaitable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery


class QueueMessagesMiddleware(BaseMiddleware):

    def __init__(self):
        super().__init__()
        self.user_queues = defaultdict(asyncio.Queue)
        self.user_tasks = {}

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

            if user_id not in self.user_tasks:
                self.user_tasks[user_id] = asyncio.create_task(self.process_queue(user_id, handler, data))

            await self.user_queues[user_id].put((event, handler, data))

    async def process_queue(self, user_id: int, handler: Callable, data: Dict[str, Any]):
        while True:
            event, handler, data = await self.user_queues[user_id].get()
            try:
                await handler(event, data)
            except Exception as e:
                error_text = "".join((traceback.format_exception(None, e, e.__traceback__)))
                print(error_text)

            self.user_queues[user_id].task_done()
