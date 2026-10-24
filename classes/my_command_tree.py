from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from constants import MSG_BLACKLIST
import my_functions

if TYPE_CHECKING:
    from classes.my_client import MyClient


class MyCommandTree(app_commands.CommandTree["MyClient"]):
    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        """Called before every slash command: returning False cancels it."""
        if interaction.user.id in self.client.blacklist:
            await my_functions.send_by_interaction(interaction, MSG_BLACKLIST)
            return False

        # Answer within 3 seconds, otherwise Discord shows "This interaction failed"
        await my_functions.send_by_interaction(interaction, "Request received")
        return True
