import types
from typing import Any

import discord

from queue_action import QueueAction
from action import Action


class Server:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self._queue_add_musics = QueueAction()
        self._queue_others_requests = QueueAction()
        self._text_channel = None

    def add_in_queue_add_musics(self, action: Action):
        self._queue_add_musics.add_in_queue(action)

    def add_in_queue_others_requests(self, action: Action):
        self._queue_others_requests.add_in_queue(action)
