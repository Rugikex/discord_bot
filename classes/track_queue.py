from __future__ import annotations
import datetime
import math
import random
from typing import TYPE_CHECKING

import discord

from classes.callback_button import CallbackButton
from classes.track import Track
from constants import QUEUE_REACTIONS
import my_functions
import voice_gestion

if TYPE_CHECKING:
    from classes.current_track import CurrentTrack
    from classes.my_client import MyClient
    from classes.guild_player import GuildPlayer


class TrackQueue:
    def __init__(self) -> None:
        self._tracks: list[Track] = []
        self._message: discord.Message | None = None

    def has_next_track(self) -> bool:
        return len(self._tracks) > 0

    @property
    def next_track(self) -> Track:
        return self._tracks.pop(0)

    @property
    def queue_size(self) -> int:
        return len(self._tracks)

    async def clear_queue(
        self, interaction: discord.Interaction[MyClient] | None
    ) -> bool:
        if interaction is not None:
            voice_client: (
                discord.VoiceClient | None
            ) = await voice_gestion.check_voice_client(interaction)
            if voice_client is None:
                return False

        self._tracks = []
        return True

    async def delete_message(self) -> None:
        await my_functions.delete_msg(self._message)
        self._message = None

    def get_queue_total_time(
        self, current_track: CurrentTrack | None
    ) -> datetime.timedelta:
        res: datetime.timedelta = datetime.timedelta(0)
        item: Track
        for item in self._tracks:
            res += item.duration

        if current_track is not None:
            res += current_track.track.duration
            res -= current_track.audio.progress_datetime

        return res - datetime.timedelta(microseconds=res.microseconds)

    async def move_track(
        self,
        interaction: discord.Interaction[MyClient],
        position: int,
        new_position: int,
    ) -> None:
        if not self._tracks:
            await my_functions.reply(interaction, "Queue is empty!", private=True)
            return

        if (
            new_position < 1
            or position < 1
            or position > len(self._tracks)
            or new_position > len(self._tracks)
        ):
            await my_functions.reply(
                interaction, "Numbers are incorrect!", private=True
            )
            return

        track: Track = self._tracks.pop(position - 1)
        self._tracks.insert(new_position - 1, track)

        await my_functions.reply(
            interaction,
            f"Move {track} from position {position} to position {new_position}.",
        )

    async def remove_tracks(
        self,
        interaction: discord.Interaction[MyClient],
        begin: int,
        end: int,
        send_msg: bool = True,
    ) -> None:
        voice_client: (
            discord.VoiceClient | None
        ) = await voice_gestion.check_voice_client(interaction)
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
            await my_functions.reply(interaction, f"Remove {counter} track(s).")

    async def get_queue(
        self, interaction: discord.Interaction[MyClient], page: int, is_new: bool = True
    ) -> None:
        voice_client: discord.VoiceClient | None = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return

        if len(self._tracks) == 0:
            await my_functions.reply(interaction, "Queue is empty!", private=True)
            return

        if page <= 0:
            await my_functions.reply(
                interaction, "Number page is incorrect!", private=True
            )
            return

        if page != 1 and not self._tracks[(page - 1) * 10 : page * 10]:
            await my_functions.reply(
                interaction, "Number page is too big!", private=True
            )
            return

        content: str = self.create_message_content(interaction, page)

        if self._message and is_new:
            await my_functions.delete_msg(self._message)

        if self._message and not is_new:
            await my_functions.edit_message(self._message, content=content)
            await self.edit_buttons_on_message_queue(self._message, page)
        else:
            self._message = await my_functions.send_by_channel(
                interaction.channel, content
            )
            if self._message:
                await self.create_buttons_on_message_queue(self._message, page)

    async def add_in_queue(
        self,
        interaction: discord.Interaction[MyClient],
        tracks: list[Track],
        position: int | None,
        content: str,
        shuffle: bool,
    ) -> None:
        if position is not None:
            i: int
            track: Track
            for i, track in enumerate(tracks):
                self._tracks.insert(position - 1 + i, track)
            if len(tracks) > 1:
                await my_functions.reply(
                    interaction,
                    f"Added {len(tracks)} tracks to {position} at "
                    f"{position + len(tracks)} in queue.\n"
                    f'From: "{content}".',
                )
            else:
                await my_functions.reply(
                    interaction,
                    f'Added in position {position} to queue: "{tracks[0]}".\n'
                    f'From: "{content}".',
                )
        else:
            self._tracks.extend(tracks)
            if len(tracks) > 1:
                await my_functions.reply(
                    interaction,
                    f'Added {len(tracks)} tracks to queue.\nFrom: "{content}".',
                )
            else:
                await my_functions.reply(
                    interaction,
                    f'Added to queue: "{tracks[0]}".\nFrom: "{content}".',
                )

        if shuffle:
            await self.shuffle_queue(interaction)

    async def shuffle_queue(self, interaction: discord.Interaction[MyClient]) -> bool:
        voice_client: discord.VoiceClient | None = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return False

        random.seed()
        random.shuffle(self._tracks)
        return True

    def create_message_content(
        self, interaction: discord.Interaction[MyClient], page: int
    ) -> str:
        max_page: int = max(math.ceil(len(self._tracks) / 10), 1)
        player: GuildPlayer = interaction.client.get_player(interaction.guild_id)
        number_tracks: int = 0 if player.current_track is None else 1
        msg_content: str = f"Queue list (page {page}/{max_page}):\n"
        if page == 1 and player.current_track is not None:
            current_track: CurrentTrack = player.current_track
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
            f"__Total time:__ {self.get_queue_total_time(player.current_track)}"
        )
        return msg_content

    def create_view_queue(self, page: int) -> discord.ui.View:
        view: discord.ui.View = discord.ui.View()

        async def previous_page(interaction: discord.Interaction[MyClient]) -> None:
            await interaction.response.defer()
            await self.get_queue(interaction, page - 1, is_new=False)

        async def next_page(interaction: discord.Interaction[MyClient]) -> None:
            await interaction.response.defer()
            await self.get_queue(interaction, page + 1, is_new=False)

        view.add_item(
            CallbackButton(previous_page, emoji=QUEUE_REACTIONS[0], disabled=page == 1)
        )
        view.add_item(
            CallbackButton(
                next_page,
                emoji=QUEUE_REACTIONS[1],
                disabled=not self._tracks[page * 10 :],
            )
        )
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

    async def stop_track(self, interaction: discord.Interaction[MyClient]) -> None:
        voice_client: discord.VoiceClient | None = await voice_gestion.get_voice_client(
            interaction
        )
        if voice_client is None:
            return

        self._tracks = []
        player: GuildPlayer | None = interaction.client.find_player(
            interaction.guild_id
        )
        if player is not None:
            player.stop_looping()

        voice_client.stop()
        await my_functions.reply(interaction, "The bot stops playing tracks.")
