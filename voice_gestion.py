import asyncio
import random
import re

import discord
import yt_dlp

from classes.audio_source_tracked import AudioSourceTracked
from classes.specific_searches import SpecificSearches
import globals_var
import my_functions
import youtube_requests


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 3",
    "options": "-vn -loglevel quiet",
}


async def user_is_connected(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.User) or interaction.user.voice is None:
        await my_functions.send_by_channel(
            interaction.channel,
            "You have to be connected to a voice channel in this server!",
        )
        return False

    return True


async def next_music(interaction: discord.Interaction, guild_id: int) -> None:
    voice_client = await get_voice_client(interaction, check=False)
    server = globals_var.client_bot.get_server(guild_id)
    queue_musics = server.get_queue_musics()

    if (
        queue_musics.has_next_music() or server.is_looping()
    ) and voice_client is not None:
        if server.is_looping() and server.has_current_music_info():
            new_music = server.get_current_music_info().get_music()
        else:
            new_music = queue_musics.get_next_music()

        with yt_dlp.YoutubeDL(globals_var.ydl_opts) as ydl:
            info = await globals_var.client_bot.loop.run_in_executor(
                None, ydl.extract_info, new_music.link
            )

        url = None
        if info:
            for info_format in info["formats"]:
                if "asr" not in info_format:
                    continue
                url = info_format["url"]
                break

        if url is None:
            await my_functions.send_by_channel(
                interaction.channel,
                f'Can\'t find stream for listening "{new_music}".\n'
                f"The music is skipped.",
            )
            await next_music(interaction, guild_id)
            return

        raw_audio = discord.FFmpegPCMAudio(
            url,
            before_options=FFMPEG_OPTIONS["before_options"],
            options=FFMPEG_OPTIONS["options"],
        )

        audio = AudioSourceTracked(raw_audio)

        await server.set_current_music_info(interaction, new_music, audio)

        voice_client.play(
            audio,
            after=lambda x=None: asyncio.run_coroutine_threadsafe(
                next_music(interaction, guild_id), globals_var.client_bot.loop
            ),
        )
    else:
        await server.clear_current_and_queue_messages()


async def get_voice_client(
    interaction: discord.Interaction, check: bool = True
) -> discord.VoiceClient | None:
    if check and not await user_is_connected(interaction):
        return None

    guilds_id = list(
        map(lambda n: n.channel.guild.id, globals_var.client_bot.voice_clients)
    )
    if interaction.guild_id not in guilds_id:
        await my_functions.send_by_channel(
            interaction.channel, "I'm not connected to this server."
        )
        return None

    channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if check and interaction.user.voice.channel not in channels:
        await my_functions.send_by_channel(
            interaction.channel, "We are in different voice channels."
        )
        return None

    for voice_client in globals_var.client_bot.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.guild != interaction.guild:
            continue
        return voice_client

    return None


async def check_voice_client(
    interaction: discord.Interaction,
) -> discord.VoiceClient | None:
    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        return None

    if voice_client.source is None:
        await my_functions.send_by_channel(interaction.channel, "No music is playing.")
        return None

    return voice_client


async def client_is_disconnected(interaction: discord.Interaction) -> bool:
    voice_client: discord.VoiceClient = discord.utils.get(
        globals_var.client_bot.voice_clients, guild=interaction.guild
    )
    if not voice_client:
        return True

    return False


async def pause_music(interaction: discord.Interaction) -> None:
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if voice_client.is_paused():
        await my_functions.send_by_channel(
            interaction.channel, "The music is already paused."
        )
        return

    voice_client.pause()

    await my_functions.send_by_channel(interaction.channel, "The music is paused.")


async def resume_music(interaction: discord.Interaction) -> None:
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await my_functions.send_by_channel(
            interaction.channel, "The music is already playing."
        )
        return

    voice_client.resume()

    await my_functions.send_by_channel(interaction.channel, "The music resumes.")


async def skip_music(interaction: discord.Interaction, number: int) -> None:
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    real_number = number - 1  # Because the first music is the current music

    server = globals_var.client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()
    if server.has_current_music_info():
        music_playing_skip = server.get_current_music_info().get_music()
    else:
        music_playing_skip = None

    await queue_musics.remove_musics(
        interaction, 1, real_number, send_msg=False
    )  # 1 because the pop(begin - 1)

    voice_client.stop()

    if music_playing_skip:
        await my_functions.send_by_channel(
            interaction.channel, f"Skip {music_playing_skip}."
        )


async def disconnect(interaction: discord.Interaction) -> None:
    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        return

    await my_functions.disconnect_bot(voice_client, interaction.guild_id)
    await my_functions.send_by_channel(interaction.channel, "The bot is disconnected.")


async def is_connected(
    interaction: discord.Interaction, channel: discord.VoiceChannel
) -> bool:
    voice_channels = list(
        map(lambda n: n.channel, globals_var.client_bot.voice_clients)
    )
    if channel in voice_channels:  # Already connected
        return True
    try:
        await channel.connect(timeout=1.5, self_deaf=True)
    except asyncio.TimeoutError:
        await my_functions.send_by_channel(
            interaction.channel, "I can't connect to this channel!"
        )
        return False
    except discord.errors.ClientException:
        await my_functions.send_by_channel(
            interaction.channel,
            "Already connected to {}.".format(
                list(
                    set(voice_channels).intersection(interaction.guild.voice_channels)
                )[0].name
            ),
        )
        return False

    globals_var.client_bot.add_server(interaction.guild_id)
    globals_var.my_logger.info(f"Bot connects to {interaction.guild.name}.")
    return True


async def select_specific_search(
    interaction: discord.Interaction, number: int, content: str
) -> None:
    server = globals_var.client_bot.get_server(interaction.guild_id)
    specific_search = server.get_specifics_searches()

    if specific_search is None:
        return

    music = specific_search.get_music(number)
    shuffle = specific_search.get_shuffle()
    position = specific_search.get_position()

    if interaction.user.voice is None:
        await interaction.response.defer()
        return

    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        return

    await specific_search.delete_message()

    queue_musics = server.get_queue_musics()

    shuffle_queue = shuffle and not position

    await queue_musics.add_in_queue(
        interaction, [music], position, content, shuffle_queue
    )

    if not voice_client.is_playing():
        await next_music(interaction, interaction.guild_id)


async def create_button_select(number: int, content: str) -> discord.ui.Button:
    button = discord.ui.Button(emoji=globals_var.reactions_song[number])

    async def button_callback(interaction: discord.Interaction):
        await select_specific_search(interaction, number, content)

    button.callback = button_callback
    return button


async def play(
    interaction: discord.Interaction,
    content: str,
    shuffle: bool = False,
    position: int | None = None,
) -> None:
    if not await user_is_connected(interaction):
        return

    if not await is_connected(interaction, interaction.user.voice.channel):
        return

    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        await my_functions.send_by_channel(
            interaction.channel, "I have been disconnected."
        )
        return

    server = globals_var.client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()

    if position and (position < 1 or position > queue_musics.get_queue_size()):
        position = None

    if re.match(
        "^((https://)?(www\.|music\.)?(youtube|youtu.be)\.com/playlist\?list=.+)",
        content,
    ) or re.match(
        "^((https://)?(www\.|music\.)?(youtube|youtu.be)\.com/watch\?v=.+&list=[^&]+)",
        content,
    ):
        message = await my_functions.send_by_channel(
            interaction.channel, "Loading playlist..."
        )
        server.set_loading_playlist_message(message)
        musics = await youtube_requests.playlist_link(interaction, content)
    elif re.match(
        "^((https://)?(www\.|music\.)?(youtube|youtu.be)(\.com)?/(watch\?v=)?.+)",
        content,
    ):
        await my_functions.send_by_channel(interaction.channel, "Loading music...")
        musics = await youtube_requests.single_link(content)
    else:
        if server.has_specifics_searches():
            await my_functions.delete_msg(server.get_specifics_searches().get_message())

        message = await my_functions.send_by_channel(
            interaction.channel, f"Searching for music related to {content}."
        )

        searches = youtube_requests.specific_search(content)

        if await client_is_disconnected(interaction):
            return

        if not searches:
            await my_functions.edit_message(
                message, content=f'No music found for "{content}".'
            )
            return

        specific_search = SpecificSearches(
            searches, shuffle, interaction.user, message, position
        )
        server.set_specifics_searches(specific_search)

        msg_content = f"Select a track with buttons.\n\n"
        for i in range(len(searches)):
            msg_content += f"**{i + 1}:** {searches[i]}\n"

        view = discord.ui.View()
        for i in range(len(searches)):
            view.add_item(await create_button_select(i, content))

        await my_functions.edit_message(message, content=msg_content, view=view)
        return

    if await client_is_disconnected(interaction):
        return

    if musics == [None]:
        await my_functions.send_by_channel(
            interaction.channel,
            f"The bot is already looking for another playlist. Please wait and retry.",
        )
        return

    if not musics and re.match(
        "^(https://)?www\.youtube\.com/watch\?v=[^&\n]+((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)("
        "&list=[^&\n]+)?)",
        content,
    ):
        match = re.match(
            "^(https://)?(www\.youtube\.com/watch\?v=[^&\n]+)((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)(&list=["
            "^&\n]+)?)",
            content,
        )

        await my_functions.send_by_channel(
            interaction.channel, "No playlist found, loading music..."
        )
        if match:
            if match.lastindex:
                index = match.lastindex - 1
            else:
                index = 0
            musics = await youtube_requests.single_link(match[index])

    if not musics:
        await my_functions.send_by_channel(
            interaction.channel, f'No audio found for "{content}".'
        )
        return

    if shuffle and position:
        random.seed()
        random.shuffle(musics)

    shuffle_queue = shuffle and not position

    await queue_musics.add_in_queue(
        interaction, musics, position, content, shuffle_queue
    )

    voice_client = await get_voice_client(interaction, check=False)
    if voice_client is None:
        return
    if not voice_client.is_playing():
        await next_music(interaction, interaction.guild_id)
