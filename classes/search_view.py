from __future__ import annotations
from typing import TYPE_CHECKING

import discord

from constants import SEARCH_TIMEOUT, SONG_REACTIONS
import my_functions

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from classes.search_results import SearchResults

    # Add the chosen track, return False if it can't be selected (yet)
    OnSelect = Callable[[discord.Interaction, SearchResults, int], Awaitable[bool]]


class SearchView(discord.ui.View):
    """Buttons to choose a track of a search, usable only by its author."""

    def __init__(self, search_results: SearchResults, on_select: OnSelect) -> None:
        super().__init__(timeout=SEARCH_TIMEOUT)
        self._search_results: SearchResults = search_results
        self._on_select: OnSelect = on_select
        for number in range(len(search_results.tracks)):
            self.add_item(self._create_button(number))

    def _create_button(self, number: int) -> discord.ui.Button:
        button: discord.ui.Button = discord.ui.Button(emoji=SONG_REACTIONS[number])

        async def button_callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            if await self._on_select(interaction, self._search_results, number):
                self.stop()  # Only one selection per search

        button.callback = button_callback
        return button

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        """Called before every button callback: returning False cancels it."""
        if interaction.user.id == self._search_results.user.id:
            return True

        await interaction.response.send_message(
            f"Only {self._search_results.user.mention} can choose a track.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self) -> None:
        # Expired buttons stay visible but fail: remove the whole message
        await self._search_results.delete_message()


async def show_search_results(
    interaction: discord.Interaction, search_results: SearchResults, on_select: OnSelect
) -> None:
    """Send the tracks of a search with a button for each."""
    content: str = "Select a track with buttons.\n\n" + "".join(
        f"**{i + 1}:** {track}\n" for i, track in enumerate(search_results.tracks)
    )
    # Permanent: deleted on selection or when the buttons expire
    search_results.message = await my_functions.send_by_channel(
        interaction.channel,
        content,
        permanent=True,
        view=SearchView(search_results, on_select),
    )
