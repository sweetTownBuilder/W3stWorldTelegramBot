"""This file represents configurations from files and environment."""
import os
import logging
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Bot configuration."""

    token: str = os.getenv('BOT_TOKEN')
    tg_group_id: str = os.getenv('TG_GROUP_ID')
    DEFAULT_LOCALE: str = 'en'


@dataclass
class DifyConfig:
    api_key: str = os.getenv('DIFY_API_KEY')
    base_url: str = os.getenv('DIFY_BASE_URL')


@dataclass
class Configuration:
    """All in one configuration's class."""
    logging_level = logging.INFO

    bot = BotConfig()
    dify = DifyConfig()


conf = Configuration()
