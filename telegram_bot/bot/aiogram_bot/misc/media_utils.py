from typing import List, Union

from aiogram import Bot, types
from aiogram.utils.media_group import MediaGroupBuilder


async def copy_post(
        data: Union[List[types.Message], types.Message],
        chat_id: int,
        bot: Bot,
        caption_add: str = None,
        replace_caption: bool = False,
        reply_markup=None,
):
    async def get_media(
            data_: Union[List[types.Message], types.Message],
            caption_add_: str = None,
            replace_caption_: bool = False
    ):
        if isinstance(data_, list):
            caption = getattr(data_[0], 'html_text', '')
            if caption_add_:
                if replace_caption_:
                    caption = caption
                else:
                    caption += caption_add_
            media_group = MediaGroupBuilder(caption=caption)
            for msg in data_:
                type_msg = msg.content_type.value
                try:
                    media = getattr(msg, type_msg)[0].file_id
                except TypeError:
                    media = getattr(msg, type_msg).file_id
                media_group.add(type=type_msg, media=media, parse_mode='HTML')

            return media_group
        else:
            message = data_

            return message

    data = await get_media(data, caption_add, replace_caption_=replace_caption)
    if isinstance(data, types.Message):
        return [await bot.copy_message(chat_id, data.chat.id, data.message_id, reply_markup=reply_markup)]
    else:
        return await bot.send_media_group(chat_id, data.build())
