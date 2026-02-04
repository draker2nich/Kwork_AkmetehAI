import logging
import os

from aiogram import types

from bot.database.requests import products as db

logger = logging.getLogger(__name__)


async def send_item_content(message: types.Message, item, caption: str,
                            reply_markup: types.InlineKeyboardMarkup | None = None):
    """
    sends item content (text/photo/video/document/pptx) to the chat
    Handles file_id failures by fallback to file_path and updating DB.
    """
    sent_success = False
    logger.info(f"Attempting to send item {item.id} (type={item.content_type}) to chat {message.chat.id}")

    # try text
    if item.content_type == "text":
        await message.answer(caption, reply_markup=reply_markup)
        logger.info(f"Sent text item {item.id}")
        return

    # try file_id
    if item.file_id:
        try:
            if item.content_type == "photo":
                await message.answer_photo(item.file_id, caption=caption, reply_markup=reply_markup)
            elif item.content_type == "video":
                await message.answer_video(item.file_id, caption=caption, reply_markup=reply_markup)
            elif item.content_type in ("document", "pptx"):
                await message.answer_document(item.file_id, caption=caption, reply_markup=reply_markup)
            sent_success = True
            logger.info(f"Sent item {item.id} using file_id")
        except Exception as e:
            logger.warning(f"Failed to send item {item.id} by file_id: {e}. Retrying from disk...")
            await db.update_item(item.id, file_id=None)
            item.file_id = None
            sent_success = False

    if sent_success:
        return

    # try file_path
    if item.file_path and os.path.exists(item.file_path):
        try:
            input_file = types.FSInputFile(item.file_path)
            msg = None

            if item.content_type == "photo":
                msg = await message.answer_photo(input_file, caption=caption, reply_markup=reply_markup)
            elif item.content_type == "video":
                msg = await message.answer_video(input_file, caption=caption, reply_markup=reply_markup)
            elif item.content_type in ("document", "pptx"):
                msg = await message.answer_document(input_file, caption=caption, reply_markup=reply_markup)

            # save new file_id
            if msg:
                new_file_id = None
                if item.content_type == "photo" and msg.photo:
                    new_file_id = msg.photo[-1].file_id
                elif item.content_type == "video" and msg.video:
                    new_file_id = msg.video.file_id
                elif item.content_type in ("document", "pptx") and msg.document:
                    new_file_id = msg.document.file_id

                if new_file_id:
                    await db.update_item(item.id, file_id=new_file_id)
                    logger.info(f"Sent item {item.id} using file_path. Updated file_id to {new_file_id}")
                else:
                    logger.info(f"Sent item {item.id} using file_path (no file_id captured)")
                    
        except Exception as e:
            logger.error(f"Failed to send item {item.id} from disk: {e}")
            await message.answer(f"{caption}\n\n❌ Ошибка при отправке файла.", reply_markup=reply_markup)
    else:
        logger.warning(f"Item {item.id} file not found at path: {item.file_path}")
        await message.answer(f"{caption}\n\n❌ Файл не найден.", reply_markup=reply_markup)