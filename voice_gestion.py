from __future__ import annotations
import asyncio
import random
import re
from typing import TYPE_CHECKING

import discord
import yt_dlp

from classes.audio_source_tracked import AudioSourceTracked
from classes.search_results import SearchResults
import globals_var
import my_functions
import youtube_requests

if TYPE_CHECKING:
    from classes.server import Server
    from classes.track import Track
    from classes.track_queue import TrackQueue

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


async def next_track(interaction: discord.Interaction, guild_id: int) -> None:
    voice_client: discord.VoiceClient = await get_voice_client(interaction, False)
    if voice_client is None:
        return
    server: Server = globals_var.client_bot.get_server(guild_id)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue

    if (track_queue.has_next_track() or server.is_looping) and voice_client is not None:
        new_track: Track
        if server.is_looping and server.current_track is not None:
            new_track = server.current_track.track
        else:
            new_track = track_queue.next_track

        with yt_dlp.YoutubeDL(globals_var.ydl_opts) as ydl:
            info: dict = await globals_var.client_bot.loop.run_in_executor(
                None, ydl.extract_info, new_track.link
            )

        url: str | None = None
        if info:
            for info_format in info["formats"]:
                if "asr" not in info_format:
                    continue
                url = info_format["url"]
                break

        if url is None:
            await my_functions.send_by_channel(
                interaction.channel,
                f'Can\'t find stream for listening "{new_track}".\n'
                f"The track is skipped.",
            )
            await next_track(interaction, guild_id)
            return

        raw_audio: discord.FFmpegPCMAudio = discord.FFmpegPCMAudio(
            url,
            before_options=FFMPEG_OPTIONS["before_options"],
            options=FFMPEG_OPTIONS["options"],
        )

        audio: AudioSourceTracked = AudioSourceTracked(raw_audio)

        await server.update_current_track(interaction, new_track, audio)

        voice_client.play(
            audio,
            after=lambda x=None: asyncio.run_coroutine_threadsafe(
                next_track(interaction, guild_id), globals_var.client_bot.loop
            ),
        )
    else:
        await server.clear_current_and_queue_messages()


async def get_voice_client(
    interaction: discord.Interaction, check: bool = True
) -> discord.VoiceClient | None:
    if check and not await user_is_connected(interaction):
        return None

    guilds_id: list[int] = list(
        map(lambda n: n.channel.guild.id, globals_var.client_bot.voice_clients)
    )
    if interaction.guild_id not in guilds_id:
        await my_functions.send_by_channel(
            interaction.channel, "I'm not connected to this server."
        )
        return None

    channels: list[discord.VoiceChannel] = list(
        map(lambda n: n.channel, globals_var.client_bot.voice_clients)
    )
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
    voice_client: discord.VoiceClient = await get_voice_client(interaction)
    if voice_client is None:
        return None

    if voice_client.source is None:
        await my_functions.send_by_channel(interaction.channel, "No track is playing.")
        return None

    return voice_client


async def client_is_disconnected(interaction: discord.Interaction) -> bool:
    voice_client: discord.VoiceClient = discord.utils.get(
        globals_var.client_bot.voice_clients, guild=interaction.guild
    )
    if not voice_client:
        return True

    return False


async def pause_track(interaction: discord.Interaction) -> None:
    voice_client: discord.VoiceClient = await check_voice_client(interaction)
    if voice_client is None:
        return

    if voice_client.is_paused():
        await my_functions.send_by_channel(
            interaction.channel, "The track is already paused."
        )
        return

    voice_client.pause()

    await my_functions.send_by_channel(interaction.channel, "The track is paused.")


async def resume_track(interaction: discord.Interaction) -> None:
    voice_client: discord.VoiceClient = await check_voice_client(interaction)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await my_functions.send_by_channel(
            interaction.channel, "The track is already playing."
        )
        return

    voice_client.resume()

    await my_functions.send_by_channel(interaction.channel, "The track resumes.")


async def skip_track(interaction: discord.Interaction, number: int) -> None:
    voice_client: discord.VoiceClient = await check_voice_client(interaction)
    if voice_client is None:
        return

    real_number: int = number - 1  # Because the first track is the current track

    server: Server = globals_var.client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue

    track_to_skip: Track | None
    if server.current_track is not None:
        track_to_skip = server.current_track.track
    else:
        track_to_skip = None

    await track_queue.remove_tracks(
        interaction, 1, real_number, send_msg=False
    )  # 1 because the pop(begin - 1)

    voice_client.stop()

    if track_to_skip:
        await my_functions.send_by_channel(
            interaction.channel, f"Skip {track_to_skip}."
        )


async def disconnect(interaction: discord.Interaction) -> None:
    voice_client: discord.VoiceClient | None = await get_voice_client(interaction)
    if voice_client is None:
        return

    await my_functions.disconnect_bot(voice_client, interaction.guild_id)
    await my_functions.send_by_channel(interaction.channel, "The bot is disconnected.")


async def is_connected(
    interaction: discord.Interaction, channel: discord.VoiceChannel
) -> bool:
    voice_channels: list[discord.VoiceChannel] = list(
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
            f"Already connected to {list(set(voice_channels).intersection(interaction.guild.voice_channels))[0].name}.",
        )
        return False

    globals_var.client_bot.add_server(interaction.guild_id)
    globals_var.my_logger.info("Bot connects to %s.", interaction.guild.name)
    return True


async def select_specific_search(
    interaction: discord.Interaction, number: int, content: str
) -> None:
    server: Server = globals_var.client_bot.get_server(interaction.guild_id)

    search_results: SearchResults | None = server.search_results
    if search_results is None:
        return

    track: Track = search_results.get_track(number)
    shuffle: bool = search_results.shuffle
    position: int | None = search_results.position

    if interaction.user.voice is None:
        await interaction.response.defer()
        return

    voice_client: discord.VoiceClient | None = await get_voice_client(interaction)
    if voice_client is None:
        return

    await search_results.delete_message()

    track_queue: TrackQueue = server.track_queue

    shuffle_queue: bool = shuffle and not position

    await track_queue.add_in_queue(
        interaction, [track], position, content, shuffle_queue
    )

    if not voice_client.is_playing():
        await next_track(interaction, interaction.guild_id)


async def create_button_select(number: int, content: str) -> discord.ui.Button:
    button: discord.ui.Button = discord.ui.Button(
        emoji=globals_var.reactions_song[number]
    )

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

    voice_client: discord.VoiceClient | None = await get_voice_client(interaction)
    if voice_client is None:
        await my_functions.send_by_channel(
            interaction.channel, "I have been disconnected."
        )
        return

    server: Server = globals_var.client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue

    if position and (position < 1 or position > track_queue.queue_size):
        position = None

    message: discord.Message | None = None
    tracks: list[Track] | list[None] | None = None
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
        server.loading_playlist_message = message
        tracks = await youtube_requests.playlist_link(interaction, content)
    elif re.match(
        "^((https://)?(www\.|music\.)?(youtube|youtu.be)(\.com)?/(watch\?v=)?.+)",
        content,
    ):
        await my_functions.send_by_channel(interaction.channel, "Loading track...")
        tracks = await youtube_requests.single_link(content)
    else:
        if server.search_results is not None:
            await my_functions.delete_msg(server.search_results.message)

        message = await my_functions.send_by_channel(
            interaction.channel, f"Searching for track related to {content}."
        )

        searches: list[Track] = youtube_requests.specific_search(content)

        if await client_is_disconnected(interaction):
            return

        if not searches:
            await my_functions.edit_message(
                message, content=f'No track found for "{content}".'
            )
            return

        search_results: SearchResults = SearchResults(
            searches, shuffle, interaction.user, message, position
        )
        server.search_results = search_results

        msg_content: str = "Select a track with buttons.\n\n"
        for i, track in enumerate(searches):
            msg_content += f"**{i + 1}:** {track}\n"

        view: discord.ui.View = discord.ui.View()
        for i in range(len(searches)):
            view.add_item(await create_button_select(i, content))

        await my_functions.edit_message(message, content=msg_content, view=view)
        return

    if await client_is_disconnected(interaction):
        return

    if tracks == [None]:
        await my_functions.send_by_channel(
            interaction.channel,
            "The bot is already looking for another playlist. Please wait and retry.",
        )
        return

    if not tracks and re.match(
        "^(https://)?www\.youtube\.com/watch\?v=[^&\n]+((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)("
        "&list=[^&\n]+)?)",
        content,
    ):
        match: re.Match[str] | None = re.match(
            "^(https://)?(www\.youtube\.com/watch\?v=[^&\n]+)((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)(&list=["
            "^&\n]+)?)",
            content,
        )

        await my_functions.send_by_channel(
            interaction.channel, "No playlist found, loading track..."
        )
        if match:
            index: int
            if match.lastindex:
                index = match.lastindex - 1
            else:
                index = 0
            tracks = await youtube_requests.single_link(match[index])

    if not tracks:
        await my_functions.send_by_channel(
            interaction.channel, f'No audio found for "{content}".'
        )
        return

    if shuffle and position:
        random.seed()
        random.shuffle(tracks)

    shuffle_queue: bool = shuffle and not position

    await track_queue.add_in_queue(
        interaction, tracks, position, content, shuffle_queue
    )

    voice_client: discord.VoiceClient = await get_voice_client(interaction, check=False)
    if voice_client is None:
        return
    if not voice_client.is_playing():
        await next_track(interaction, interaction.guild_id)
