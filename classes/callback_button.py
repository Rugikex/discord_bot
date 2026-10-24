from __future__ import annotations
from typing import TYPE_CHECKING, Any, override

import discord

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from classes.my_client import MyClient

type OnClick = Callable[[discord.Interaction[MyClient]], Awaitable[None]]


class CallbackButton(discord.ui.Button):
    """Button calling on_click, typed unlike `button.callback = function`."""

    def __init__(self, on_click: OnClick, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._on_click: OnClick = on_click

    @override
    async def callback(self, interaction: discord.Interaction[Any]) -> None:
        await self._on_click(interaction)
