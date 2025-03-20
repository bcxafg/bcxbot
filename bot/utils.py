from typing import Dict, Any
from telegram import Update
from logger import logger

def log_update(update: Update) -> None:
    """Log incoming update information"""
    if update.message:
        logger.info(
            f"Received message from {update.message.from_user.username} "
            f"(id: {update.message.from_user.id}): {update.message.text}"
        )

