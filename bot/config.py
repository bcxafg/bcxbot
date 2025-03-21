import os

# debug mode
DEBUG = bool(int(os.getenv('DEBUG')))

# Bot Configuration
if DEBUG:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_TEST', '')  # Bot token should be set in environment variables
else:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')  # Bot token should be set in environment variables

# Параметры вебхука
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN', '')
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}"

# Параметры веб-сервера
WEBAPP_HOST = '0.0.0.0'  # Слушать на всех интерфейсах
WEBAPP_PORT = 8443


# Command descriptions
COMMANDS = {
    'start': 'Start the bot and see welcome message',
    'help': 'Show all available commands and their usage',
    'eur': 'Get EUR conversion chart. Usage: /eur [amount][currency] [R±rate%]\nExample: /eur 100USD R-2',
    'usd': 'Get USD conversion chart. Usage: /usd [amount][currency] [R±rate%]',
    'aed': 'Get AED conversion chart. Usage: /aed [amount][currency] [R±rate%]',
    'pln': 'Get PLN conversion chart. Usage: /pln [amount][currency] [R±rate%]',
    'rub': 'Get RUB conversion chart. Usage: /rub [amount][currency] [R±rate%]',
    'rico': 'Get current exchange rates from Rico.ge',
    'groupid': 'Get the ID of the current chat group'
}

# Messages
WELCOME_MESSAGE = """
👋 Welcome to the Currency Chart Bot!

🔹 Currency Commands:
/eur - Get EUR conversion chart
/usd - Get USD conversion chart
/aed - Get AED conversion chart
/pln - Get PLN conversion chart
/rub - Get RUB conversion chart
/rico - Get Rico.ge exchange rates

🔢 Calculator Feature:
Just start with a number to calculate!
Examples:
• /2+3 = 5
• /2*2+2 = 6
• /10/2 = 5

📝 Currency Usage Examples:
• /eur - Get random EUR amount chart
• /eur 100 - Convert 100 EUR
• /eur 100USD - Convert 100 USD to EUR
• /eur 100 R-2 - Apply -2% rate adjustment

✨ Inline Mode:
Type @botname followed by a command to use inline mode:
• @botname /eur 100 usd
• @botname /usd 50 eur
• @botname 2+2

Use /help for detailed information about all commands.
"""

ERROR_MESSAGE = "Sorry, something went wrong. Please try again later."

HELP_MESSAGE = """
📚 *Currency Chart Bot Help*

💱 Currency Commands:
All currency commands support these formats:
• /{currency} - Random amount
• /{currency} 100 - Specific amount
• /{currency} 100USD - Convert from USD
• /{currency} 100 R±2 - Adjust rate by ±2%

🧮 Calculator Usage:
Start with a number to calculate expressions:
• /2+3 - Addition
• /10*5 - Multiplication
• /15/3 - Division
• /8-4 - Subtraction
• /2*2+2 - Multiple operations

✨ Inline Mode:
Use the bot in any chat by typing @botname followed by:
• /eur 100 usd - Convert currencies
• /usd 50 eur - Another conversion
• 2+2 - Calculate expressions

*Available Commands:*
"""