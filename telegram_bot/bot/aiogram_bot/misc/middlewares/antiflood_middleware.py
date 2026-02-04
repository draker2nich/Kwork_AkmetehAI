import datetime
from typing import Dict, Any, Callable, Awaitable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery


class AntiFloodMiddleware(BaseMiddleware):
    time_updates: Dict[int, datetime.datetime] = {}
    message_counts: Dict[int, int] = {}
    timedelta_limiter: datetime.timedelta = datetime.timedelta(seconds=1)
    max_messages_per_second: int = 2

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id

            if user_id in self.time_updates.keys():
                current_time = datetime.datetime.now()
                if (current_time - self.time_updates[user_id]) > self.timedelta_limiter:
                    self.message_counts[user_id] = 1
                    self.time_updates[user_id] = current_time
                else:
                    self.message_counts[user_id] += 1

                if self.message_counts[user_id] > self.max_messages_per_second:
                    return None
            else:
                self.message_counts[user_id] = 1
                self.time_updates[user_id] = datetime.datetime.now()
            data["update_db"] = True
            return await handler(event, data)
