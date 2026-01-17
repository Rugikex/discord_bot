import os
import discord
from dotenv import load_dotenv
from googleapiclient.discovery import build

from constants import *
from logger_setup import my_logger, ydl_opts
from classes.music_source import MusicSource, ServerSource, YoutubeSource
from classes.my_client import MyClient


MUSIC_SOURCES: dict[str, MusicSource] = {
    "server": ServerSource(),
    "youtube": YoutubeSource(),
}

load_dotenv()

youtube_key = os.getenv("YOUTUBE_KEY")
if not youtube_key:
    raise KeyError("No YOUTUBE_KEY found")
youtube = build("youtube", "v3", developerKey=youtube_key)

discord_key = os.getenv("DISCORD_KEY")
if not discord_key:
    raise KeyError("No DISCORD_KEY found")

client_bot = MyClient(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client_bot)
