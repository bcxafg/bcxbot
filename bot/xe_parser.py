import re
from logger import logger
import trafilatura

def parse_XE_rates(input_str: str) -> float:
    """
    Parse XE.com HTML content to extract exchange rate.
    Returns: exchange rate as float
    """
    try:
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")

        # Strip HTML tags using trafilatura
        clean_text = trafilatura.extract(input_str, include_links=False, include_formatting=False)
        if not clean_text:
            raise ValueError("Failed to extract clean text from HTML")

        # Log clean text preview
        logger.info(f"Clean text preview: {clean_text[:1000]}")

        # Initialize variables
        from_amount = None
        to_amount = None

        # Extract amounts using regex - match any number followed by any word(s)
        pattern = r'(\d{1,3}(?:,\d{3})*|\d+)\.\d+\s+[A-Za-z\s]+=\s*(\d{1,3}(?:,\d{3})*|\d+)\.\d+\s+[A-Za-z\s]+'
        amounts = re.search(pattern, clean_text)

        if not amounts:
            logger.error("No matching amounts found in text")
            logger.debug(f"Full cleaned text: {clean_text}")
            raise ValueError("Could not find currency amounts in the text")

        amount_str = amounts.group(0)
        logger.info(f"Found amount string: {amount_str}")

        # Remove all non-numeric characters except dots and equals
        amount_str = re.sub(r"[^0-9.=]", "", amount_str)
        logger.info(f"Cleaned amount string: {amount_str}")

        # Split by equals sign and convert to float
        amounts_parts = amount_str.split('=')
        if len(amounts_parts) != 2:
            raise ValueError(f"Invalid amount format: {amount_str}")

        from_amount = float(amounts_parts[0])
        to_amount = float(amounts_parts[1])

        logger.info(f"Parsed amounts - From: {from_amount}, To: {to_amount}")

        if from_amount <= 0:
            raise ValueError("Source amount must be greater than 0")

        # Calculate and return rate
        exchange_rate = round(to_amount / from_amount, 7)
        logger.info(f"Calculated exchange rate: {exchange_rate}")

        return exchange_rate

    except Exception as e:
        logger.error(f"Error parsing XE rates: {str(e)}")
        raise ValueError(f"Failed to parse exchange rate: {str(e)}")