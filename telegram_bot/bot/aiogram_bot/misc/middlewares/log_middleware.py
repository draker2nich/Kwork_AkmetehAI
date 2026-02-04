import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram import types

logger = logging.getLogger(__name__)


class LogMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: types.TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        event_type = type(event).__name__
        event_data = event.text if isinstance(event, types.Message) else event.data
        logger.info(
            f"{event_type}: {event_data} FROM {event.from_user.id} ({event.from_user.username} | {event.from_user.full_name})")

        return await handler(event, data)
