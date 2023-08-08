import datetime
import math
import random
from typing import List

import discord

from classes.music_item import MusicItem
import globals_var
import my_functions
import voice_gestion


class QueueMusic:
    def __init__(self) -> None:
        self.musics: List[MusicItem] = []
        self.message: discord.Message | None = None
        self.is_new: bool = True

    def has_next_music(self) -> bool:
        return len(self.musics) > 0

    def get_next_music(self) -> MusicItem:
        return self.musics.pop(0)

    def get_queue_size(self) -> int:
        return len(self.musics)

    async def clear_queue(self, interaction: discord.Interaction | None) -> None:
        if interaction is not None:
            voice_client = await voice_gestion.check_voice_client(interaction)
            if voice_client is None:
                return

        self.musics = []

    async def delete_message(self) -> None:
        await my_functions.delete_msg(self.message)
        self.message = None

    def get_queue_total_time(self, guild_id: int | None) -> datetime.timedelta:
        if guild_id is None:
            raise Exception("Server not found")

        res = datetime.timedelta(0)
        for item in self.musics:
            if isinstance(item.duration, datetime.timedelta):
                res += item.duration

        server = globals_var.client_bot.get_server(guild_id)
        current_music_info = server.get_current_music_info()
        if current_music_info:
            current_music_duration = current_music_info.get_music().duration
            if isinstance(current_music_duration, datetime.timedelta):
                res += current_music_duration
            res -= current_music_info.get_audio().progress_datetime

        return res - datetime.timedelta(microseconds=res.microseconds)

    async def move_music(
        self, interaction: discord.Interaction, position: int, new_position: int
    ):
        if not self.musics:
            await my_functions.send_by_channel(interaction.channel, "Queue is empty!")
            return

        if (
            new_position < 1
            or position < 1
            or len(self.musics) + 1 < position
            or len(self.musics) + 1 < new_position
        ):
            await my_functions.send_by_channel(
                interaction.channel, "Numbers are incorrect!"
            )
            return

        music = self.musics.pop(position - 1)
        self.musics.insert(new_position - 1, music)

        await my_functions.send_by_channel(
            interaction.channel,
            f"Move {music} from position {position} to position {new_position}.",
        )

    async def remove_musics(
        self,
        interaction: discord.Interaction,
        begin: int,
        end: int,
        send_msg: bool = True,
    ):
        voice_client = await voice_gestion.check_voice_client(interaction)
        if voice_client is None:
            return

        counter = 0
        for _ in range(begin, end + 1):
            if self.musics:
                self.musics.pop(begin - 1)
                counter += 1
            else:
                break

        if send_msg:
            await my_functions.send_by_channel(
                interaction.channel, f"Remove {counter} music(s)."
            )

    async def get_queue(
        self, interaction: discord.Interaction, page: int, is_new: bool = True
    ):
        voice_client = await voice_gestion.get_voice_client(interaction)
        if voice_client is None:
            return

        if not self.musics:
            await my_functions.send_by_channel(interaction.channel, "Queue is empty!")
            return

        if page <= 0:
            await my_functions.send_by_channel(
                interaction.channel, "Number page is incorrect!"
            )
            return

        if page != 1 and not self.musics[(page - 1) * 10 : page * 10]:
            await my_functions.send_by_channel(
                interaction.channel, "Number page is too big!"
            )
            return

        content = self.message_queue(interaction, page)

        if self.message and is_new:
            await my_functions.delete_msg(self.message)

        if self.message and not is_new:
            await my_functions.edit_message(self.message, content=content)
            await self.edit_buttons_on_message_queue(self.message, page)
        else:
            self.message = await my_functions.send_by_channel(
                interaction.channel, content
            )
            if self.message:
                await self.create_buttons_on_message_queue(self.message, page)

    async def add_in_queue(
        self,
        interaction: discord.Interaction,
        musics: List[MusicItem],
        position: int,
        content: str,
    ):
        if position is not None:
            for i in range(len(musics)):
                self.musics.insert(position - 1 + i, musics[i])
            if len(musics) > 1:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f"Added {len(musics)} musics to {position} at "
                    f"{position + len(musics)} in queue.\n"
                    f'From: "{content}".',
                )
            else:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f'Added in position {position} to queue: "{musics[0]}".\n'
                    f'From: "{content}".',
                )
        else:
            self.musics.extend(musics)
            if len(musics) > 1:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f"Added {len(musics)} musics to queue.\n" f'From: "{content}".',
                )
            else:
                await my_functions.send_by_channel(
                    interaction.channel,
                    f'Added to queue: "{musics[0]}".\n' f'From: "{content}".',
                )

        if self.is_new:
            wololo = MusicItem(
                "Welcome",
                datetime.timedelta(seconds=2),
                "https://www.youtube.com/watch?v=hSU0Z3_466s",
            )
            self.musics.insert(0, wololo)
            self.is_new = False

    async def shuffle_queue(self, interaction: discord.Interaction):
        voice_client = await voice_gestion.get_voice_client(interaction)
        if voice_client is None:
            return

        random.seed()
        random.shuffle(self.musics)

    def message_queue(self, interaction: discord.Interaction, page: int) -> str:
        number_musics = 1
        max_page = max(math.ceil(len(self.musics) / 10), 1)
        server = globals_var.client_bot.get_server(interaction.guild_id)
        msg_content = f"Queue list (page {page}/{max_page}):\n"
        if page == 1 and server.has_current_music_info():
            current_music_info = server.get_current_music_info()
            msg_content += f"**Now.** {current_music_info.get_music().title} ["
            msg_content += current_music_info.get_audio().progress_str

            msg_content += f" / {current_music_info.get_music().duration}]\n"

        if self.musics:
            for i in range(len(self.musics[(page - 1) * 10 : page * 10])):
                number = i + (page - 1) * 10
                msg_content += f"**{number + 1}.** {self.musics[number]}\n"
            number_musics += len(self.musics)

        msg_content += (
            f"__Total musics:__ {number_musics}\n"
            f"__Total time:__ {self.get_queue_total_time(interaction.guild_id)}"
        )
        return msg_content

    def create_view_queue(self, page: int) -> discord.ui.View:
        view = discord.ui.View()
        button = discord.ui.Button(emoji=globals_var.reactions_queue[0])

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
        if not self.musics[page * 10 :]:
            button.disabled = True
        view.add_item(button)

        return view

    async def create_buttons_on_message_queue(
        self, message: discord.Message, page: int
    ):
        view = self.create_view_queue(page)

        await my_functions.edit_message(message, view=view)

    async def edit_buttons_on_message_queue(self, message: discord.Message, page: int):
        view = self.create_view_queue(page)

        await my_functions.edit_message(message, view=view)
