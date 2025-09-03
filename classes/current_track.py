from __future__ import annotations
from typing import TYPE_CHECKING

from my_functions import delete_msg

if TYPE_CHECKING:
    import discord

    from classes.audio_source_tracked import AudioSourceTracked
    from classes.track import Track


class CurrentTrack:
    def __init__(
        self,
        track: Track,
        message: discord.Message | None,
        audio: AudioSourceTracked,
    ) -> None:
        self._track: Track = track
        self._message: discord.Message | None = message
        self._audio: AudioSourceTracked = audio

    @property
    def track(self) -> Track:
        return self._track

    @property
    def message(self) -> discord.Message | None:
        return self._message

    @property
    def audio(self) -> AudioSourceTracked:
        return self._audio

    async def delete_message(self) -> None:
        await delete_msg(self._message)
        self._message = None

    def update(
        self,
        track: Track,
        message: discord.Message | None,
        audio: AudioSourceTracked,
    ) -> None:
        self._track = track
        self._message = message
        self._audio = audio
