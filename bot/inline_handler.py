from aiogram import Router, F, Dispatcher
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.enums import ParseMode
from handlers import calculate_result
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    """Handle inline query for math calculations."""
    try:
        query_text = query.query.strip()
        logger.info(f"Processing inline math query: {query_text}")

        raw_result = None  # добавил, чтоб не было ошибки на 51й строке

        if not query_text:
            results = [
                InlineQueryResultArticle(
                    id='help',
                    title="Calculator Help",
                    description="Type a math expression (e.g., 2+2)",
                    input_message_content=InputTextMessageContent(
                        message_text="*Calculator Usage:*\nType a math expression (e.g., 2+2)",
                        parse_mode=ParseMode.MARKDOWN
                    )
                )
            ]
        else:
            if not query_text.startswith('/'):
                query_text = '/' + query_text

            result, raw_result = calculate_result(query_text)

            results = [
                InlineQueryResultArticle(
                    id='1',
                    title=f"Calculate: {query_text[1:]}",
                    description=str(raw_result) if raw_result is not None else "Invalid expression",
                    input_message_content=InputTextMessageContent(
                        message_text=result,
                        parse_mode=ParseMode.MARKDOWN if raw_result is not None else None
                    )
                )
            ]

        await query.answer(results, cache_time=1)
        if raw_result is not None:
            logger.info(f"Successfully calculated inline query: {query_text}")
        else:
            logger.warning(f"Failed to calculate inline query: {query_text}")

    except Exception as e:
        logger.error(f"Error in inline query handler: {str(e)}")
        await query.answer([
            InlineQueryResultArticle(
                id='error',
                title="Error",
                description="An error occurred. Please try again.",
                input_message_content=InputTextMessageContent(
                    message_text="Sorry, an error occurred. Please try again."
                )
            )
        ], cache_time=1)


def register_inline_handler(dp: Dispatcher):
    """Register inline handler"""
    dp.include_router(router)
