from __future__ import annotations
import datetime
import math
import random
from typing import TYPE_CHECKING

import discord

from classes.track import Track
import globals_var
import my_functions
import voice_gestion

if TYPE_CHECKING:
    from classes.current_track import CurrentTrack
    from classes.server import Server


class TrackQueue:
    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._message: discord.Message | None = None
        self._is_new: bool = True

    def has_next_track(self) -> bool:
        return len(self._tracks) > 0

    @property
    def next_track(self) -> Track:
        return self._tracks.pop(0)

    @property
    def queue_size(self) -> int:
        return len(self._tracks)

    async def clear_queue(self, interaction: discord.Interaction | None) -> None:
        if interaction is not None:
            voice_client: discord.VoiceClient | None = (
                await voice_gestion.check_voice_client(interaction)
            )
            if voice_client is None:
                return

        self._tracks = []

    async def delete_message(self) -> None:
        await my_functions.delete_msg(self._message)
        self._message = None

    def get_queue_total_time(self, guild_id: int | None) -> datetime.timedelta:
        if guild_id is None:
            raise ValueError("Server ID must not be None")

        res: datetime.timedelta = datetime.timedelta(0)
        item: Track
        for item in self._tracks:
            res += item.duration

        server: Server = globals_var.client_bot.get_server(guild_id)
        current_track: CurrentTrack | None = server.current_track
        if current_track is not None:
            res += current_track.track.duration
            res -= current_track.audio.progress_datetime

        return res - datetime.timedelta(microseconds=res.microseconds)

    async def move_track(
        self, interaction: discord.Interaction, position: int, new_position: int
    ) -> None:
        if not self._tracks:
            await my_functions.send_by_channel(interaction.channel, "Queue is empty!")
            return

        if (
            new_position < 1
            or position < 1
            or len(self._tracks) + 1 < position
            or len(self._tracks) + 1 < new_position
        ):
            await my_functions.send_by_channel(
                interaction.channel, "Numbers are incorrect!"
            )
            return

        track: Track = self._tracks.pop(position - 1)
        self._tracks.insert(new_position - 1, track)

        await my_functions.send_by_channel(
            interaction.channel,
            f"Move {track} from position {position} to position {new_position}.",
        )

    async def remove_tracks(
        self,
        interaction: discord.Interaction,
        begin: int,
        end: int,
        send_msg: bool = True,
    ) -> None:
        voice_client: discord.VoiceClient = await voice_gestion.check_voice_client(
            interaction
        )
        if voice_client is None:
            return

        counter: int = 0
        for _ in range(begin, end + 1):
            if len(self._tracks) >= begin:
                self._tracks.pop(begin - 1)
                counter += 1
            else:
                break

        if send_msg:
            await my_functions.send_by_channel(
                interaction.channel, f"Remove {counter} track(s)."
            )

    async def get_queue(
        self, interaction: discord.Interaction, page: int, is_new: bool = True
    ):
        voice_client: discord.VoiceClient = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return

        if len(self._tracks) == 0:
            await my_functions.send_by_channel(interaction.channel, "Queue is empty!")
            return

        if page <= 0:
            await my_functions.send_by_channel(
                interaction.channel, "Number page is incorrect!"
            )
            return

        if page != 1 and not self._tracks[(page - 1) * 10 : page * 10]:
            await my_functions.send_by_channel(
                interaction.channel, "Number page is too big!"
            )
            return

        content: str = self.create_message_content(interaction, page)

        if self._message and is_new:
            await my_functions.delete_msg(self._message)

        if self._message and not is_new:
            await my_functions.edit_message(self._message, content=content)
            await self.edit_buttons_on_message_queue(self._message, page)
        else:
            self._message: discord.Message = await my_functions.send_by_channel(
                interaction.channel, content
            )
            if self._message:
                await self.create_buttons_on_message_queue(self._message, page)

    async def add_in_queue(
        self,
        interaction: discord.Interaction,
        tracks: list[Track],
        position: int,
        content: str,
        shuffle: bool,
    ):
        if position is not None:
            i: int
            track: Track
            for i, track in enumerate(self._tracks):
                self._tracks.insert(position - 1 + i, track)
            if len(tracks) > 1:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f"Added {len(tracks)} tracks to {position} at "
                    f"{position + len(tracks)} in queue.\n"
                    f'From: "{content}".',
                )
            else:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f'Added in position {position} to queue: "{tracks[0]}".\n'
                    f'From: "{content}".',
                )
        else:
            self._tracks.extend(tracks)
            if len(tracks) > 1:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f"Added {len(tracks)} tracks to queue.\n" f'From: "{content}".',
                )
            else:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f'Added to queue: "{tracks[0]}".\n' f'From: "{content}".',
                )

        if shuffle:
            await self.shuffle_queue(interaction)

        if self._is_new:
            # TODO: remove hardcoded track
            wololo: Track = Track(
                "Welcome",
                datetime.timedelta(seconds=2),
                "https://www.youtube.com/watch?v=hSU0Z3_466s",
                interaction.user,
            )
            self._tracks.insert(0, wololo)
            self._is_new = False

    async def shuffle_queue(self, interaction: discord.Interaction):
        voice_client: discord.VoiceClient = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return

        random.seed()
        random.shuffle(self._tracks)

    def create_message_content(
        self, interaction: discord.Interaction, page: int
    ) -> str:
        number_tracks: int = 1
        max_page: int = max(math.ceil(len(self._tracks) / 10), 1)
        server: Server = globals_var.client_bot.get_server(interaction.guild_id)
        msg_content: str = f"Queue list (page {page}/{max_page}):\n"
        if page == 1 and server.current_track is not None:
            current_track: CurrentTrack = server.current_track
            msg_content += f"**Now.** {current_track.track.title} ["
            msg_content += current_track.audio.progress_str

            msg_content += f" / {current_track.track.duration}]\n"

        if self._tracks:
            for i in range(len(self._tracks[(page - 1) * 10 : page * 10])):
                number: int = i + (page - 1) * 10
                msg_content += f"**{number + 1}.** {self._tracks[number]}\n"
            number_tracks += len(self._tracks)

        msg_content += (
            f"__Total tracks:__ {number_tracks}\n"
            f"__Total time:__ {self.get_queue_total_time(interaction.guild_id)}"
        )
        return msg_content

    def create_view_queue(self, page: int) -> discord.ui.View:
        view: discord.ui.View = discord.ui.View()
        button: discord.ui.Button = discord.ui.Button(
            emoji=globals_var.reactions_queue[0]
        )

        async def button_callback_down(interaction: discord.Interaction) -> None:
            await self.get_queue(interaction, page - 1, is_new=False)
            await interaction.response.defer()

        button.callback = button_callback_down
        if page == 1:
            button.disabled = True
        view.add_item(button)

        button = discord.ui.Button(emoji=globals_var.reactions_queue[1])

        async def button_callback_up(interaction: discord.Interaction):
            await self.get_queue(interaction, page + 1, is_new=False)

        button.callback = button_callback_up
        if not self._tracks[page * 10 :]:
            button.disabled = True
        view.add_item(button)

        return view

    async def create_buttons_on_message_queue(
        self, message: discord.Message, page: int
    ) -> None:
        view: discord.ui.View = self.create_view_queue(page)

        await my_functions.edit_message(message, view=view)

    async def edit_buttons_on_message_queue(
        self, message: discord.Message, page: int
    ) -> None:
        view: discord.ui.View = self.create_view_queue(page)

        await my_functions.edit_message(message, view=view)

    async def stop_track(self, interaction: discord.Interaction) -> None:
        voice_client: discord.VoiceClient = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return

        self._tracks: list[Track] = []

        voice_client.stop()
        await my_functions.send_by_channel(
            interaction.channel, "The bot stops playing tracks."
        )
