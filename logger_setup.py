import logging
from typing import Any


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
        # Align levelname to 8 characters for consistent formatting
        levelname_raw: str = record.levelname
        levelname_aligned: str = f"{levelname_raw:<8}"
        # Then apply color
        record.levelname = (
            f"{self.LEVEL_COLOR.get(record.levelno)}{levelname_aligned}{self.RESET}"
        )

        record.name = f"{self.GREEN}{record.name}{self.RESET}"
        return super().format(record)


class YDLLogger:
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("yt-dlp")
        self.logger.setLevel(logging.ERROR)

        # To avoid duplicates if the class is instantiated multiple times
        if self.logger.handlers == []:
            handler: logging.StreamHandler = logging.StreamHandler()
            formatter: ColorFormatter = ColorFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, msg: Any) -> None:
        # For compatibility with yt-dlp, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith("[debug] "):
            self.logger.debug(msg)
        else:
            self.info(msg)

    def info(self, msg: Any) -> None:
        self.logger.info(msg)

    def warning(self, msg: Any) -> None:
        self.logger.warning(msg)

    def error(self, msg: Any) -> None:
        # Ignore "Video unavailable" errors
        if "Video unavailable" in msg:
            return
        # Remove "ERROR: " prefix
        msg = msg[msg.index(" [") + 1 :] if " [" in msg else msg
        self.logger.error(msg)


logging.getLogger("discord.player").setLevel(logging.WARNING)
logging.getLogger("discord.voice_client").setLevel(logging.WARNING)
logging.getLogger("discord.voice_state").setLevel(logging.WARNING)

my_logger: logging.Logger = logging.getLogger("discord_bot")
handler: logging.StreamHandler = logging.StreamHandler()
formatter: ColorFormatter = ColorFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
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
    "logger": YDLLogger(),
    "youtube_include_dash_manifest": False,
    "ignoreerrors": True,
    "ratelimit": 1_000_000,
    "concurrent_fragment_downloads": 1,
}
