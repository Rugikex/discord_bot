import logging
import os

import discord
from dotenv import load_dotenv
from googleapiclient.discovery import build

from classes.my_client import MyClient

logging.getLogger("discord.player").setLevel(logging.WARNING)
logging.getLogger("discord.voice_client").setLevel(logging.WARNING)
logging.getLogger("pytube").setLevel(logging.ERROR)

my_logger = logging.getLogger("Discord_bot")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
my_logger.addHandler(handler)
my_logger.setLevel(logging.INFO)


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

discord_key = os.getenv("DISCORD_KEY")
if discord_key is None:
    raise Exception("No DISCORD_KEY find")
client_bot = MyClient(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client_bot)

youtube_key = os.getenv("YOUTUBE_KEY")
if youtube_key is None:
    raise Exception("No YOUTUBE_KEY find")
youtube = build("youtube", "v3", developerKey=youtube_key)

skip_seconds = 10.0
add_queue_seconds = 5.0

reactions_song = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
reactions_queue = ["⬆️", "⬇️"]


def initialize():
    global client_bot, youtube, tree, my_logger
