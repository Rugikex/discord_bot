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
    global reactions_song, reactions_queue, client_bot, youtube, tree, my_logger
