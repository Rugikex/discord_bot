import os

import discord
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

discord_key = os.getenv("DISCORD_KEY")
client_bot = discord.Client(intents=discord.Intents.all())
tree = discord.app_commands.CommandTree(client_bot)

youtube_key = os.getenv("YOUTUBE_KEY")
youtube = build("youtube", "v3", developerKey=youtube_key)

"""Can be change
Store by guild id
Contains:
    'start_time': date the music started or restart after pause,
    'time_spent': duration spent after the last time the music was paused,
    'music': music currently playing,
    'is_paused': check if the music is paused,
    'message': message that display which music is currently playing
"""
current_music = {}
"""
Store by guild id
Contains:
    'searches': list of 1 to 5 MusicItem about the last search terms
    'shuffle': boolean to know if the music must be shuffled
    'user': user who requested the song
    'message': message that shows searches
"""
specifics_searches = {}
"""
Store by guild id
Contains a list of MusicItem(s) if users request multiples musics
"""
queues_musics = {}

reactions_song = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
reactions_queue = ["⬆️", "⬇️"]
prefix = 'tk'


def initialize():
    global current_music, specifics_searches, queues_musics, reactions_song, reactions_queue, client_bot, youtube, tree
