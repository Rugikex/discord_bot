from __future__ import annotations
from typing import TYPE_CHECKING

from classes.current_track import CurrentTrack
from classes.track_queue import TrackQueue
import my_functions

if TYPE_CHECKING:
    import discord

    from classes.audio_source_tracked import AudioSourceTracked
    from classes.search_results import SearchResults
    from classes.track import Track


class Server:
    def __init__(self, server_id: int) -> None:
        self._server_id: int = server_id
        self._current_track: CurrentTrack | None = None
        self._search_results: SearchResults | None = None
        self._track_queue: TrackQueue = TrackQueue()
        self._loading_playlist_message: discord.Message | None = None
        self._is_disconnected: bool = False
        self._is_looping: bool = False

    @property
    def server_id(self) -> int:
        return self._server_id

    @property
    def current_track(self) -> CurrentTrack | None:
        return self._current_track

    async def update_current_track(
        self,
        interaction: discord.Interaction,
        track: Track,
        audio: AudioSourceTracked,
    ) -> None:
        message: discord.Message | None
        embed: discord.Embed
        file: discord.File
        embed, file = my_functions.create_embed(track, self._is_looping)
        if self._current_track is None:
            message = await my_functions.send_by_channel(
                interaction.channel, "", permanent=True, embed=embed, file=file,
            )
            # message = await my_functions.send_by_channel(
            #     interaction.channel, f"Now playing {track}.", permanent=True
            # )
            self._current_track = CurrentTrack(track, message, audio)
            return

        last_message: discord.Message | None
        try:
            if hasattr(interaction.channel, "history"):
                last_message = [
                    message async for message in interaction.channel.history(limit=1)
                ][0]
            else:
                last_message = None
        except discord.errors.Forbidden:
            last_message = None

        if (
            last_message is not None
            and self._current_track.message is not None
            and last_message.id != self._current_track.message.id
        ):
            await self._current_track.delete_message()

            message = await my_functions.send_by_channel(
                interaction.channel, "", permanent=True, embed=embed, file=file
            )
        elif self._current_track.message is not None:
            message = await my_functions.edit_message(
                self._current_track.message, "", embed=embed
            )
        else:
            message = await my_functions.send_by_channel(
                interaction.channel, "", permanent=True, embed=embed, file=file
            )
        self._current_track.update(track, message, audio)

    @property
    def search_results(self) -> SearchResults | None:
        return self._search_results

    @search_results.setter
    def search_results(self, value: SearchResults | None) -> None:
        self._search_results = value

    @property
    def track_queue(self) -> TrackQueue:
        return self._track_queue

    @property
    def loading_playlist_message(self) -> discord.Message | None:
        return self._loading_playlist_message

    @loading_playlist_message.setter
    def loading_playlist_message(
        self, loading_playlist_message: discord.Message | None
    ) -> None:
        self._loading_playlist_message = loading_playlist_message

    @property
    def is_disconnected(self) -> bool:
        return self._is_disconnected

    def disconnect(self) -> None:
        self._is_disconnected = True

    @property
    def is_looping(self) -> bool:
        return self._is_looping

    def switch_looping(self) -> None:
        self._is_looping = not self._is_looping

    async def clear_current_and_queue_messages(self) -> None:
        if self._current_track is not None:
            await self._current_track.delete_message()
        await self._track_queue.delete_message()
        self._current_track = None

    async def clear(self) -> None:
        await self.clear_current_and_queue_messages()
        await my_functions.delete_msg(self._loading_playlist_message)
        if self._search_results is not None:
            await self._search_results.delete_message()
        # TODO: Delete other message
