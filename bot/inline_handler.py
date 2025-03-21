
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from handlers import calculate_result
from logger import logger

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline query for math calculations."""
    try:
        query = update.inline_query
        if not query:
            logger.warning("Received empty inline query")
            return

        query_text = query.query.strip()
        logger.info(f"Processing inline math query: {query_text}")

        if not query_text:
            # Provide help text for empty queries
            results = [
                InlineQueryResultArticle(
                    id='help',
                    title="Calculator Help",
                    description="Type a math expression (e.g., 2+2)",
                    input_message_content=InputTextMessageContent(
                        message_text="*Calculator Usage:*\nType a math expression (e.g., 2+2)",
                        parse_mode=ParseMode.HTML.value
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
                        parse_mode=ParseMode.HTML.value if raw_result is not None else None
                    )
                )
            ]

        await query.answer(results)
        if raw_result is not None:
            logger.info(f"Successfully calculated inline query: {query_text}")
        else:
            logger.warning(f"Failed to calculate inline query: {query_text}")

    except Exception as e:
        logger.error(f"Error in inline query handler: {str(e)}")
        # Provide error feedback to user
        try:
            await query.answer([
                InlineQueryResultArticle(
                    id='error',
                    title="Error",
                    description="An error occurred. Please try again.",
                    input_message_content=InputTextMessageContent(
                        message_text="Sorry, an error occurred. Please try again."
                    )
                )
            ])
        except Exception as e2:
            logger.error(f"Failed to send error message: {str(e2)}")
