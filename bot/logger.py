import logging
import sys
from datetime import datetime

# Configure logging
def setup_logger():
    logger = logging.getLogger('TelegramBot')
    logger.setLevel(logging.INFO)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(log_format)
    f_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

logger = setup_logger()
