import random
import re
import aiohttp
import asyncio
import logging
from aiogram import Router, F, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from config import WELCOME_MESSAGE, ERROR_MESSAGE, COMMANDS, HELP_MESSAGE
from logger import logger
from screenshot import fetch_urlbox_screenshot
from xe_parser import parse_XE_rates
from datetime import datetime, timezone
import pytz
from simpleeval import simple_eval
from typing import Dict, Any, Tuple


logger = logging.getLogger(__name__)
router = Router()


def is_math_expression(text: str) -> bool:
    if not text:
        return False
    text = text[1:] if text.startswith('/') else text
    if not text or not text[0].isdigit():
        return False
    return bool(re.match(r'^[\d+\-*/\s.()]+$', text))

def calculate_result(expression: str) -> tuple[str, float | None]:
    try:
        if not expression:
            raise ValueError("Expression cannot be empty")

        expression = expression[1:] if expression.startswith('/') else expression
        expression = expression.replace(' ', '')

        if not is_math_expression(expression):
            error_msg = ("❌ Error: Invalid expression\n\n"
                        "Examples:\n"
                        "• /2+3 (addition)\n"
                        "• /10*5 (multiplication)\n"
                        "• /15/3 (division)\n"
                        "• /8-4 (subtraction)\n"
                        "• /2*2+2 (multiple operations)")
            return error_msg, None

        result = simple_eval(expression)
        formatted_result = int(result) if isinstance(result, float) and result.is_integer() else round(result, 2)

        response = (
            f"```\n"
            f"{expression} = {formatted_result}\n"
            f"```\n"
            f"Result: `{formatted_result}`"
        )

        return response, formatted_result

    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        return f"❌ Error: {str(e)}", None

@router.message(CommandStart())
async def start_command(message: Message):
    """Handle the /start command"""
    logger.info(f"User {message.from_user.username} (ID: {message.from_user.id}) started the bot")
    await message.reply(WELCOME_MESSAGE, parse_mode=ParseMode.HTML.value)

@router.message(Command("help"))
async def help_command(message: Message):
    """Handle the /help command"""
    help_text = HELP_MESSAGE
    for cmd, desc in COMMANDS.items():
        help_text += f"\n/{cmd} - {desc}"
    await message.reply(help_text, parse_mode=ParseMode.HTML.value)


async def parse_currency_input(args: list, base_currency: str = "EUR") -> tuple:
    amount = float(random.randint(1, 10000))
    from_currency = base_currency
    to_currency = "USD" if base_currency != "USD" else "EUR"
    rate_adjustment = 1.0

    logger.info(
        f"Processing currency input with args: {args}, base_currency: {base_currency}"
    )

    if args:
        input_text = args[0].upper()
        logger.info(f"Processing input text: {input_text}")

        if len(input_text) == 3 and input_text.isalpha():
            to_currency = input_text
            logger.info(f"Detected currency code: {to_currency}")
        elif len(input_text) >= 3 and input_text[-3:].isalpha():
            detected_currency = input_text[-3:]
            amount_str = input_text[:-3]
            if amount_str.isdigit():
                amount = float(amount_str)
                from_currency = detected_currency
                to_currency = base_currency
                logger.info(
                    f"Extracted amount: {amount}, currency: {from_currency}")
        elif input_text.isdigit():
            amount = float(input_text)
            logger.info(f"Detected amount only: {amount}")

        for arg in args[1:]:
            arg = arg.upper()
            if arg.startswith('R') or arg.startswith('+') or arg.startswith(
                    '-') or arg.endswith('%') or arg.replace('.', '',
                                                                        1).isdigit():
                try:
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
            elif len(arg) == 3 and arg.isalpha():
                to_currency = arg
                logger.info(
                    f"Found target currency in additional args: {to_currency}")

    logger.info(
        f"Final parsed values - Amount: {amount}, From: {from_currency}, To: {to_currency}, Rate: {rate_adjustment}"
    )
    return amount, from_currency, to_currency, rate_adjustment

def adjust_amount(amount: float, rate_adjustment: float = 1.0) -> float:
    float_amount = float(amount)
    return round(float_amount *
                 rate_adjustment, 2) if float_amount > 0 else float_amount

async def fetch_XE_rates(from_currency: str,
                          to_currency: str,
                          amount: float,
                          rate_adjustment: float = 1.0) -> Tuple[bytes, str]:
    logger.info(
        f"Fetching XE rates for {amount} {from_currency} to {to_currency}")

    adjusted_amount = adjust_amount(amount, rate_adjustment)
    xe_url = f"https://www.xe.com/currencyconverter/convert/?Amount={adjusted_amount}&From={from_currency}&To={to_currency}"

    image_url, html_data = await fetch_urlbox_screenshot(xe_url, scroll="300")

    caption = f"<b>{amount:,.2f} {from_currency} ➔ {to_currency}</b>"
    if rate_adjustment != 1.0:
        rate_percent = (rate_adjustment - 1) * 100
        caption += f"\n📊 Rate adjustment: {rate_percent:+.1f}%"

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

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                raise ValueError(
                    f"Failed to download image: Status {response.status}")
            image_data = await response.read()

    return image_data, caption

@router.message(Command("eur", "usd", "aed", "pln", "rub"))
async def currency_command(message: Message, base_currency: str = "EUR"):
    try:
        amount, from_currency, to_currency, rate_adjustment = await parse_currency_input(
            message.text.split()[1:], base_currency)

        progress_msg = await message.reply(
            f"🔄 Converting {from_currency} to {to_currency}...\n"
            f"Getting latest rates from XE.com...")

        try:
            image_data, caption = await fetch_XE_rates(
                from_currency=from_currency,
                to_currency=to_currency,
                amount=amount,
                rate_adjustment=rate_adjustment)

            await progress_msg.delete()

            from aiogram.types import BufferedInputFile
            photo = BufferedInputFile(image_data, filename="exchange_rate.png")
            await message.reply_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
            logger.info("Image sent successfully")

        except Exception as e:
            logger.error(f"Screenshot error: {str(e)}")
            raise
    except ValueError as e:
        logger.error(f"Value error in /{base_currency} command: {str(e)}")
        usage_example = f"/{base_currency.lower()} 100USD" if base_currency != "USD" else f"/{base_currency.lower()} 100EUR"
        await message.reply(
            f"❌ Invalid input format!\n\n"
            f"Examples:\n"
            f"• {usage_example} - Convert from USD\n"
            f"• /{base_currency.lower()} 100 - Convert {base_currency}\n"
            f"• /{base_currency.lower()} 100 R-2 - Apply -2% rate\n\n"
            f"Type /help for more information.")
    except Exception as e:
        logger.error(f"Error in /{base_currency} command: {str(e)}")
        await message.reply(
            f"😕 {ERROR_MESSAGE}\n"
            f"If this persists, please try again in a few minutes.")

async def fetch_Rico_rates() -> Tuple[bytes, str]:
    logger.info("Fetching rates from Rico.ge")

    rico_url = "https://www.rico.ge/en/"

    try:
        logger.info(
            f"Starting Rico.ge screenshot capture at {datetime.now().isoformat()}"
        )
        image_url, html_data = await fetch_urlbox_screenshot(
            url=rico_url,
            width=500,
            height=420,
            scroll=".currencies-section"
        )
        logger.info("Rico.ge screenshot captured successfully")

        tbilisi_tz = pytz.timezone('Asia/Tbilisi')
        tbilisi_time = datetime.now(tbilisi_tz).strftime("%H:%M")
        caption = f"Rico.ge Exchange Rates\n{tbilisi_time} (Tbilisi)"

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

@router.message(Command("rico"))
async def rico_command(message: Message):
    try:
        progress_msg = await message.reply(
            "Fetching latest rates from Rico.ge...")
        logger.info("Progress message sent, starting screenshot capture")

        try:
            image_data, caption = await fetch_Rico_rates()

            try:
                await progress_msg.delete()
                logger.info("Progress message deleted successfully")
            except Exception as del_err:
                logger.warning(
                    f"Non-critical error: Could not delete progress message: {del_err}"
                )

            from aiogram.types import BufferedInputFile
            photo = BufferedInputFile(image_data, filename="rico_rates.png")
            await message.reply_photo(photo=photo, caption=caption)
            logger.info("Rico.ge rates image sent successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Screenshot error in /rico command: {error_msg}")
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
        error_text = (f"😕 {ERROR_MESSAGE}\n"
                      f"If this persists, please try again in a few minutes.")
        try:
            await message.reply(error_text)
            logger.info("Error message sent to user")
        except Exception as msg_err:
            logger.error(f"❌ Failed to send error message: {msg_err}")

@router.message(F.text.startswith('/'))
async def handle_commands(message: Message):
    command = message.text.split()[0][1:].lower()
    if command in ['eur', 'usd', 'aed', 'pln', 'rub']:
        await currency_command(message, command.upper())
    elif is_math_expression(message.text):
        await math_command(message)

async def math_command(message: Message):
    expression = message.text
    logger.info(f"Processing math expression: {expression}")

    response, result = calculate_result(expression)
    await message.answer(response, parse_mode=ParseMode.HTML.value if result is not None else None)


@router.message(Command("groupid"))
async def groupid_command(message: Message):
    chat = message.chat
    user = message.from_user
    logger.info(
        f"User {user.username} (ID: {user.id}) requested group ID in chat {chat.id}"
    )

    if chat.type in ['group', 'supergroup']:
        await message.reply(
            f"📢 Group ID: `{chat.id}`\n"
            f"Group Name: *{chat.title}*",
            parse_mode=ParseMode.HTML.value)
        logger.info(f"Sent group ID information for chat {chat.id}")
    else:
        await message.reply(
            "❌ This command only works in group chats.\n"
            "Add me to a group and try again!")
        logger.info("Rejected groupid command in non-group chat")

def register_handlers(dp: Dispatcher):
    dp.include_router(router)