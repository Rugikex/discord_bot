import logging
import os
from typing import Any

import discord
from dotenv import load_dotenv
from googleapiclient.discovery import build

from classes.my_client import MyClient


class ColorFormatter(logging.Formatter):
    """Logging Formatter with colored output"""

    GRAY: str = "\033[90m"
    GREEN: str = "\033[32m"
    RESET: str = "\033[0m"

    LEVEL_COLOR = {
        logging.DEBUG: "\033[1;90m",
        logging.INFO: "\033[1;94m",
        logging.WARNING: "\033[1;33m",
        logging.ERROR: "\033[1;91m",
        logging.CRITICAL: "\033[1;31m",
    }

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Override formatTime to color the date"""
        original_time: str = super().formatTime(record, datefmt)
        return f"{self.GRAY}{original_time}{self.RESET}"

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = (
            f"{self.LEVEL_COLOR.get(record.levelno)}{record.levelname}{self.RESET}"
        )
        record.name = f"{self.GREEN}{record.name}{self.RESET}"
        return super().format(record)


class LoggerYdl:
    """
    Logger for yt-dlp
    Only print error
    """

    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith("[debug] "):
            pass
        else:
            self.info(msg)

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


logging.getLogger("discord.player").setLevel(logging.WARNING)
logging.getLogger("discord.voice_client").setLevel(logging.WARNING)
logging.getLogger("pytubefix").setLevel(logging.ERROR)

my_logger: logging.Logger = logging.getLogger("discord_bot")
handler: logging.StreamHandler = logging.StreamHandler()
formatter: ColorFormatter = ColorFormatter(
    "%(asctime)s %(levelname)s     %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
my_logger.addHandler(handler)
my_logger.setLevel(logging.INFO)

ydl_opts = {
    "audio-quality": 0,
    "simulate": True,
    "extract-audio": True,
    "format": "bestaudio",
    "fps": None,
    "logger": LoggerYdl(),
    "youtube_include_dash_manifest": False,
}

load_dotenv()

discord_key: str | None = os.getenv("DISCORD_KEY")
if discord_key is None:
    raise Exception("No DISCORD_KEY find")
client_bot: MyClient = MyClient(intents=discord.Intents.all())
tree: discord.app_commands.CommandTree = discord.app_commands.CommandTree(client_bot)

youtube_key: str | None = os.getenv("YOUTUBE_KEY")
if youtube_key is None:
    raise Exception("No YOUTUBE_KEY find")
youtube: Any = build("youtube", "v3", developerKey=youtube_key)

skip_seconds: float = 10.0
add_queue_seconds: float = 5.0

reactions_song: list[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
reactions_queue: list[str] = ["⬆️", "⬇️"]

msg_blacklist: str = "Sorry, you can't use this bot."


def initialize() -> None:
    global client_bot, youtube, tree, my_logger
