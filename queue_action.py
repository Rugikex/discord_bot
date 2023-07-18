import types
from typing import Any

import discord

from action import Action


class QueueAction:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self._queue = []

    def add_in_queue(self, action: Action):
        self._queue.append(action)

    def execute_action(self):
        action = self._queue.pop()
        return action.execute()
