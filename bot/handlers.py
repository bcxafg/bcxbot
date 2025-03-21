import random
import re
import aiohttp
import asyncio
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, MessageHandler, filters
from config import WELCOME_MESSAGE, ERROR_MESSAGE, COMMANDS, HELP_MESSAGE
from logger import logger
from screenshot import fetch_urlbox_screenshot
from xe_parser import parse_XE_rates
from datetime import datetime, timezone
import pytz
from simpleeval import simple_eval
from typing import Dict, Any, Tuple


def is_math_expression(text: str) -> bool:
    """Check if the command is a mathematical expression."""
    if not text:
        return False
    # Remove leading slash and check if it starts with a digit
    text = text[1:] if text.startswith('/') else text
    if not text or not text[0].isdigit():
        return False
    # Check if it contains only digits, operators, and spaces
    return bool(re.match(r'^[\d+\-*/\s.()]+$', text))


def calculate_result(expression: str) -> tuple[str, float | None]:
    """
    Calculate result of mathematical expression and return formatted output.

    Args:
        expression: Mathematical expression as string

    Returns:
        Tuple[str, float | None]: (formatted_message, raw_result)
        If calculation fails, raw_result will be None and message will contain error
    """
    try:
        if not expression:
            raise ValueError("Expression cannot be empty")

        # Remove leading slash and any spaces
        expression = expression[1:] if expression.startswith(
            '/') else expression
        expression = expression.replace(' ', '')

        # Validate expression
        if not is_math_expression(expression):
            error_msg = ("❌ Error: Invalid expression\n\n"
                         "Examples:\n"
                         "• /2+3 (addition)\n"
                         "• /10*5 (multiplication)\n"
                         "• /15/3 (division)\n"
                         "• /8-4 (subtraction)\n"
                         "• /2*2+2 (multiple operations)")
            return error_msg, None

        # Calculate result using simpleeval
        try:
            result = simple_eval(expression)
        except ZeroDivisionError:
            error_msg = "❌ Error: Division by zero is not allowed\n\nPlease avoid dividing by zero."
            return error_msg, None
        except Exception as e:
            logger.error(f"Calculation error: {str(e)}")
            error_msg = ("❌ Error: Invalid expression\n\n"
                         "Examples:\n"
                         "• /2+3 (addition)\n"
                         "• /10*5 (multiplication)\n"
                         "• /15/3 (division)\n"
                         "• /8-4 (subtraction)\n"
                         "• /2*2+2 (multiple operations)")
            return error_msg, None

        # Format result based on whether it's an integer or float
        formatted_result = int(result) if isinstance(
            result, float) and result.is_integer() else round(result, 2)

        # Format response with equation and copyable result
        response = (
            f"```\n"  # Start monospace block
            f"{expression} = {formatted_result}\n"
            f"```\n"  # End monospace block
            f"Result: `{formatted_result}`"  # Separate, copyable result
        )

        return response, formatted_result

    except Exception as e:
        logger.error(f"Unexpected error in calculate_result: {str(e)}")
        return f"❌ Error: {str(e)}", None


async def math_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle mathematical expression commands."""
    message = update.message
    if not message:
        return

    expression = message.text
    logger.info(f"Processing math expression: {expression}")

    response, result = calculate_result(expression)
    parse_mode = ParseMode.MARKDOWN if result is not None else None
    await message.reply_text(response, parse_mode=parse_mode)

    if result is not None:
        logger.info(f"Successfully calculated {expression}")
    else:
        logger.warning(f"Failed to calculate {expression}")


async def start_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    user = update.message.from_user
    logger.info(f"User {user.username} (ID: {user.id}) started the bot")
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode=ParseMode.HTML.value)


async def parse_currency_input(args: list,
                               base_currency: str = "EUR") -> tuple:
    """Parse the amount, currency codes, and rate from user input.
    Returns: (amount, from_currency, to_currency, rate_adjustment)
    Default: (0, base_currency, "USD", 1.0)
    Amount will be 0 if no amount was provided.
    Rate adjustment will be 1.0 if no rate was provided.
    """
    # Generate random amount if no amount provided
    amount = float(random.randint(1, 10000))  # Convert to float immediately
    from_currency = base_currency
    to_currency = "USD" if base_currency != "USD" else "EUR"
    rate_adjustment = 1.0  # Default rate adjustment

    logger.info(
        f"Processing currency input with args: {args}, base_currency: {base_currency}"
    )

    if args:
        input_text = args[0].upper()
        logger.info(f"Processing input text: {input_text}")

        # Check if input is just a 3-letter currency code
        if len(input_text) == 3 and input_text.isalpha():
            to_currency = input_text
            logger.info(f"Detected currency code: {to_currency}")
        # Try to extract currency code (last 3 chars if they're letters)
        elif len(input_text) >= 3 and input_text[-3:].isalpha():
            detected_currency = input_text[-3:]
            amount_str = input_text[:-3]
            if amount_str.isdigit():
                amount = float(amount_str)  # Convert to float
                from_currency = detected_currency
                to_currency = base_currency
                logger.info(
                    f"Extracted amount: {amount}, currency: {from_currency}")
        # If no currency code, assume it's just an amount
        elif input_text.isdigit():
            amount = float(input_text)  # Convert to float
            logger.info(f"Detected amount only: {amount}")

        # Process additional arguments
        for arg in args[1:]:
            arg = arg.upper()
            # Check for rate adjustment (handle all formats: R±N, ±N%, ±N)
            if arg.startswith('R') or arg.startswith('+') or arg.startswith(
                    '-') or arg.endswith('%') or arg.replace('.', '',
                                                                        1).isdigit():
                try:
                    # Remove R prefix, + prefix, and % suffix if present
                    rate_str = arg.lstrip('R').lstrip('+').rstrip('%')
                    rate_value = float(rate_str)
                    rate_adjustment = 1 + (rate_value /
                                              100) if rate_value >= 0 else 1 / (
                        1 + abs(rate_value) / 100)
                    logger.info(
                        f"Applied rate adjustment: {rate_adjustment} from value: {rate_value}"
                    )
                except ValueError:
                    logger.warning(f"Invalid rate adjustment value: {arg}")
            # Check for currency code
            elif len(arg) == 3 and arg.isalpha():
                to_currency = arg
                logger.info(
                    f"Found target currency in additional args: {to_currency}")

    logger.info(
        f"Final parsed values - Amount: {amount}, From: {from_currency}, To: {to_currency}, Rate: {rate_adjustment}"
    )
    return amount, from_currency, to_currency, rate_adjustment


def adjust_amount(amount: float, rate_adjustment: float = 1.0) -> float:
    """Adjust amount based on rate adjustment factor and return float with 2 decimals"""
    float_amount = float(amount)
    return round(float_amount *
                 rate_adjustment, 2) if float_amount > 0 else float_amount


async def fetch_XE_rates(from_currency: str,
                          to_currency: str,
                          amount: float,
                          rate_adjustment: float = 1.0) -> Tuple[bytes, str]:
    """
    Fetch XE rates and return image data and formatted caption.

    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        amount: Amount to convert
        rate_adjustment: Optional rate adjustment factor (default: 1.0)

    Returns:
        Tuple[bytes, str]: (image_data, caption)
    """
    logger.info(
        f"Fetching XE rates for {amount} {from_currency} to {to_currency}")

    adjusted_amount = adjust_amount(amount, rate_adjustment)
    xe_url = f"https://www.xe.com/currencyconverter/convert/?Amount={adjusted_amount}&From={from_currency}&To={to_currency}"

    # Get screenshot and HTML data
    image_url, html_data = await fetch_urlbox_screenshot(xe_url, scroll="300")

    # Format the caption with bold text using HTML
    caption = f"<b>{amount:,.2f} {from_currency} ➔ {to_currency}</b>"
    if rate_adjustment != 1.0:
        rate_percent = (rate_adjustment - 1) * 100
        caption += f"\n📊 Rate adjustment: {rate_percent:+.1f}%"

    # Add timestamp
    timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC, %d-%m-%Y")
    caption += f"\n\nXE Rate, {timestamp}"

    try:
        rate = parse_XE_rates(html_data)
        if rate > 0:
            rate_inv = 1 / rate
            caption += f"\n1 {from_currency} = {rate:.7f} {to_currency}"
            caption += f"\n1 {to_currency} = {rate_inv:.7f} {from_currency}"
            logger.info(f"Parsed XE rate: {rate}")
    except ValueError as parse_err:
        logger.warning(f"Rate parsing failed (non-critical): {parse_err}")

    # Download image data
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                raise ValueError(
                    f"Failed to download image: Status {response.status}")
            image_data = await response.read()

    return image_data, caption


async def currency_command(update: Update,
                           context: ContextTypes.DEFAULT_TYPE,
                           base_currency: str = "EUR") -> None:
    """Handle currency commands: Send currency conversion chart screenshot"""
    message = update.message
    if not message:
        return

    user = message.from_user
    logger.info(
        f"Executing /{base_currency} command for {user.username} (ID: {user.id})"
    )

    try:
        amount, from_currency, to_currency, rate_adjustment = await parse_currency_input(
            context.args, base_currency)

        # Send a progress message
        progress_msg = await message.reply_text(
            f"🔄 Converting {from_currency} to {to_currency}...\n"
            f"Getting latest rates from XE.com...")

        try:
            # Use the fetch_XE_rates function
            image_data, caption = await fetch_XE_rates(
                from_currency=from_currency,
                to_currency=to_currency,
                amount=amount,
                rate_adjustment=rate_adjustment)

            # Delete the progress message
            await progress_msg.delete()

            # Send the photo with caption using HTML parse mode
            await message.reply_photo(photo=image_data, caption=caption, parse_mode=ParseMode.HTML)
            logger.info("Image sent successfully")

        except Exception as e:
            logger.error(f"Screenshot error: {str(e)}")
            raise
    except ValueError as e:
        logger.error(f"Value error in /{base_currency} command: {str(e)}")
        usage_example = f"/{base_currency.lower()} 100USD" if base_currency != "USD" else f"/{base_currency.lower()} 100EUR"
        await message.reply_text(
            f"❌ Invalid input format!\n\n"
            f"Examples:\n"
            f"• {usage_example} - Convert from USD\n"
            f"• /{base_currency.lower()} 100 - Convert {base_currency}\n"
            f"• /{base_currency.lower()} 100 R-2 - Apply -2% rate\n\n"
            f"Type /help for more information.")
    except Exception as e:
        logger.error(f"Error in /{base_currency} command: {str(e)}")
        await message.reply_text(
            f"😕 {ERROR_MESSAGE}\n"
            f"If this persists, please try again in a few minutes.")


async def fetch_Rico_rates() -> Tuple[bytes, str]:
    """
    Fetch Rico.ge rates and return image data and formatted caption.

    Returns:
        Tuple[bytes, str]: (image_data, caption)
    """
    logger.info("Fetching rates from Rico.ge")

    rico_url = "https://www.rico.ge/en/"

    try:
        # Fetch screenshot with enhanced error handling and logging
        logger.info(
            f"Starting Rico.ge screenshot capture at {datetime.now().isoformat()}"
        )
        image_url, html_data = await fetch_urlbox_screenshot(
            url=rico_url,
            width=500,  # Optimal width for currency section
            height=420,  # Adjusted height to show full currency section
            scroll=".currencies-section"  # CSS selector for currencies
        )
        logger.info("Rico.ge screenshot captured successfully")

        # Get current time in Tbilisi
        tbilisi_tz = pytz.timezone('Asia/Tbilisi')
        tbilisi_time = datetime.now(tbilisi_tz).strftime("%H:%M")
        caption = f"Rico.ge Exchange Rates\n{tbilisi_time} (Tbilisi)"

        # Download image data
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise ValueError(
                        f"Failed to download image: Status {response.status}")
                image_data = await response.read()

        return image_data, caption

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error fetching Rico.ge rates: {error_msg}")
        raise


async def rico_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rico command: Send Rico.ge currencies section screenshot"""
    message = update.message
    if not message:
        return

    user = message.from_user
    logger.info(f"Executing /rico command for {user.username} (ID: {user.id})")

    try:
        progress_msg = await message.reply_text(
            "Fetching latest rates from Rico.ge...")
        logger.info("Progress message sent, starting screenshot capture")

        try:
            # Use the new fetch_Rico_rates function
            image_data, caption = await fetch_Rico_rates()

            # Delete progress message before sending the photo
            try:
                await progress_msg.delete()
                logger.info("Progress message deleted successfully")
            except Exception as del_err:
                logger.warning(
                    f"Non-critical error: Could not delete progress message: {del_err}"
                )

            # Send screenshot with caption
            await message.reply_photo(photo=image_data, caption=caption)
            logger.info("Rico.ge rates image sent successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Screenshot error in /rico command: {error_msg}")
            # Always try to clean up progress message on error
            try:
                await progress_msg.delete()
                logger.info("Progress message cleaned up after error")
            except Exception as del_err:
                logger.error(
                    f"❌ Failed to delete progress message during error handling: {del_err}"
                )
            raise Exception(f"Failed to fetch Rico.ge rates: {error_msg}")

    except Exception as e:
        logger.error(f"❌ Error in /rico command: {str(e)}")
        # Send user-friendly error message
        error_text = (f"😕 {ERROR_MESSAGE}\n"
                      f"If this persists, please try again in a few minutes.")
        try:
            await message.reply_text(error_text)
            logger.info("Error message sent to user")
        except Exception as msg_err:
            logger.error(f"❌ Failed to send error message: {msg_err}")


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    user = update.message.from_user
    logger.info(f"User {user.username} (ID: {user.id}) requested help")

    # Build help message
    help_text = HELP_MESSAGE
    for cmd, desc in COMMANDS.items():
        help_text += f"\n/{cmd} - {desc}"

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML.value)


async def error_handler(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unexpected errors during bot operation"""
    logger.error(f"Update {update} caused error {context.error}")

    error_message = (
        "😕 An unexpected error occurred.\n"
        "The bot team has been notified. Please try again in a few minutes.\n\n"
        "If the issue persists, you can:\n"
        "• Use /help to check command usage\n"
        "• Try a different currency or amount\n"
        "• Start a new conversation with /start")

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                error_message, parse_mode=ParseMode.HTML.value)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


async def groupid_command(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /groupid command - returns the current chat ID"""
    message = update.message
    if not message:
        return

    chat = message.chat
    user = message.from_user
    logger.info(
        f"User {user.username} (ID: {user.id}) requested group ID in chat {chat.id}"
    )

    if chat.type in ['group', 'supergroup']:
        await message.reply_text(
            f"📢 Group ID: `{chat.id}`\n"
            f"Group Name: *{chat.title}*",
            parse_mode=ParseMode.HTML.value)
        logger.info(f"Sent group ID information for chat {chat.id}")
    else:
        await message.reply_text("❌ This command only works in group chats.\n"
                                 "Add me to a group and try again!")
        logger.info("Rejected groupid command in non-group chat")