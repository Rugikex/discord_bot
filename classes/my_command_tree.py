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
            await my_functions.reply(interaction, MSG_BLACKLIST, private=True)
            return False

        # Answer within 3 seconds, otherwise Discord shows "This interaction failed".
        # Displays "thinking...", replaced by the first answer of the command.
        await interaction.response.defer(thinking=True)
        return True

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError, /
    ) -> None:
        await super().on_error(interaction, error)  # Logs the error
        # Otherwise "thinking..." stays forever
        await my_functions.reply(interaction, "Something went wrong.", private=True)
