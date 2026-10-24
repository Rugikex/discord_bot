from __future__ import annotations
import asyncio
import concurrent.futures
import random
from typing import TYPE_CHECKING

import discord

from classes.audio_source_tracked import AudioSourceTracked
from classes.music_source import MUSIC_SOURCES
from classes.music_source.local import list_local_files, load_local_tracks
from classes.track import Track
from classes.search_results import SearchResults
from logger_setup import my_logger
import my_functions

if TYPE_CHECKING:
    from classes.music_source import MusicSource
    from classes.my_client import MyClient
    from classes.guild_player import GuildPlayer
    from classes.track_queue import TrackQueue


async def user_is_connected(interaction: discord.Interaction) -> bool:
    if isinstance(interaction.user, discord.User) or interaction.user.voice is None:
        await my_functions.send_by_channel(
            interaction.channel,
            "You have to be connected to a voice channel in this server!",
        )
        return False

    return True


def _log_future_error(future: concurrent.futures.Future) -> None:
    if not future.cancelled() and future.exception() is not None:
        my_logger.error("Can't play next track.", exc_info=future.exception())


def _after_track(
    error: Exception | None, interaction: discord.Interaction[MyClient], guild_id: int
) -> None:
    """Called by discord.py from the audio thread when a track ends."""
    if error is not None:
        my_logger.error("Player error: %s", error)
    future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
        next_track(interaction, guild_id), interaction.client.loop
    )
    future.add_done_callback(_log_future_error)


async def get_welcome_track(
    player: GuildPlayer, requester: discord.User | discord.Member
) -> Track | None:
    """Build the welcome track from the guild settings, only once per connection."""
    settings: dict[str, str | None] | None = player.pop_welcome_track()
    if not settings or not settings.get("link"):
        return None

    music_source: MusicSource | None = MUSIC_SOURCES.get(
        settings.get("platform") or player.default_platform
    )
    if music_source is None:
        return None
    return await music_source.get_track(settings["link"], requester)


async def next_track(interaction: discord.Interaction[MyClient], guild_id: int) -> None:
    """Play the next track if nothing is playing (or paused)."""
    player: GuildPlayer | None = interaction.client.find_player(guild_id)
    if player is None:
        return

    async with player.play_lock:
        while True:
            voice_client: discord.VoiceClient | None = (
                interaction.guild.voice_client if interaction.guild else None
            )
            if voice_client is None or player.is_disconnected:
                return
            if voice_client.is_playing() or voice_client.is_paused():
                return  # Already started by another command

            track_queue: TrackQueue = player.track_queue
            new_track: Track
            welcome_track: Track | None = await get_welcome_track(
                player, interaction.user
            )
            is_replay: bool = player.is_looping and player.current_track is not None
            if welcome_track is not None:
                new_track = welcome_track
            elif is_replay:
                new_track = player.current_track.track
            elif track_queue.has_next_track():
                new_track = track_queue.next_track
            else:
                await player.clear_current_and_queue_messages()
                return

            url: str | None
            ffmpeg_options: dict[str, str]
            url, ffmpeg_options = await MUSIC_SOURCES[new_track.origin].get_stream_url(
                new_track
            )

            if url is None:
                if is_replay:
                    player.stop_looping()  # Avoid retrying the same track forever
                await my_functions.send_by_channel(
                    interaction.channel,
                    f'Can\'t find stream for listening "{new_track}".\n'
                    f"The track is skipped.",
                )
                continue

            if not voice_client.is_connected() or player.is_disconnected:
                return

            audio: AudioSourceTracked = AudioSourceTracked(
                discord.FFmpegPCMAudio(url, **ffmpeg_options)
            )

            await player.update_current_track(interaction, new_track, audio)

            voice_client.play(
                audio,
                after=lambda error: _after_track(error, interaction, guild_id),
            )
            return


async def get_voice_client(
    interaction: discord.Interaction, check: bool = True
) -> discord.VoiceClient | None:
    if check and not await user_is_connected(interaction):
        return None

    voice_client: discord.VoiceClient | None = (
        interaction.guild.voice_client if interaction.guild else None
    )
    if voice_client is None:
        await my_functions.send_by_channel(
            interaction.channel, "I'm not connected to this server."
        )
        return None

    if check and interaction.user.voice.channel != voice_client.channel:
        await my_functions.send_by_channel(
            interaction.channel, "We are in different voice channels."
        )
        return None

    return voice_client


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
    return interaction.guild is None or interaction.guild.voice_client is None


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


async def skip_track(interaction: discord.Interaction[MyClient], number: int) -> None:
    voice_client: discord.VoiceClient = await check_voice_client(interaction)
    if voice_client is None:
        return

    real_number: int = number - 1  # Because the first track is the current track

    player: GuildPlayer = interaction.client.get_player(interaction.guild_id)
    track_queue: TrackQueue = player.track_queue

    track_to_skip: Track | None
    if player.current_track is not None:
        track_to_skip = player.current_track.track
    else:
        track_to_skip = None

    await track_queue.remove_tracks(
        interaction, 1, real_number, send_msg=False
    )  # 1 because the pop(begin - 1)

    # Otherwise next_track replays the current track
    player.stop_looping()
    voice_client.stop()

    if track_to_skip:
        await my_functions.send_by_channel(
            interaction.channel, f"Skip {track_to_skip}."
        )


async def disconnect(interaction: discord.Interaction[MyClient]) -> None:
    voice_client: discord.VoiceClient | None = await get_voice_client(interaction)
    if voice_client is None:
        return

    await interaction.client.disconnect_bot(voice_client, interaction.guild_id)
    await my_functions.send_by_channel(interaction.channel, "The bot is disconnected.")


async def is_connected(
    interaction: discord.Interaction[MyClient], channel: discord.VoiceChannel
) -> bool:
    current_voice_client: discord.VoiceClient | None = interaction.guild.voice_client
    if current_voice_client is not None and current_voice_client.channel == channel:
        if not interaction.client.player_exists(interaction.guild_id):
            interaction.client.add_player(interaction.guild_id)
        return True
    try:
        await channel.connect(timeout=15.0, self_deaf=True)
    except asyncio.TimeoutError:
        await my_functions.send_by_channel(
            interaction.channel, "I can't connect to this channel!"
        )
        return False
    except discord.errors.ClientException:
        channel_name: str = (
            current_voice_client.channel.name
            if current_voice_client is not None
            else "another channel"
        )
        await my_functions.send_by_channel(
            interaction.channel,
            f"Already connected to {channel_name}.",
        )
        return False

    interaction.client.add_player(interaction.guild_id)
    my_logger.info("Bot connects to %s.", interaction.guild.name)
    return True


async def select_specific_search(
    interaction: discord.Interaction[MyClient],
    search_results: SearchResults,
    number: int,
) -> bool:
    """Add the chosen track of a search, return False if it can't be selected."""
    player: GuildPlayer | None = interaction.client.find_player(interaction.guild_id)
    # Bot disconnected, search replaced by a new one or already selected
    if player is None or player.search_results is not search_results:
        return False

    # The user can join the voice channel and click again
    voice_client: discord.VoiceClient | None = await get_voice_client(interaction)
    if voice_client is None:
        return False

    # Only one selection per search
    player.search_results = None

    track: Track = search_results.get_track(number)
    shuffle: bool = search_results.shuffle
    position: int | None = search_results.position

    await search_results.delete_message()

    track_queue: TrackQueue = player.track_queue

    shuffle_queue: bool = shuffle and not position

    await track_queue.add_in_queue(
        interaction, [track], position, search_results.query, shuffle_queue
    )

    await next_track(interaction, interaction.guild_id)
    return True


async def play(
    interaction: discord.Interaction[MyClient],
    content: str,
    raw_platform: discord.app_commands.Choice[str] | str | None = None,
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

    player: GuildPlayer = interaction.client.get_player(interaction.guild_id)
    track_queue: TrackQueue = player.track_queue

    platform: str
    if raw_platform is None:
        platform = player.default_platform
    elif isinstance(raw_platform, str):
        platform = raw_platform
    else:
        platform = raw_platform.value

    if platform not in MUSIC_SOURCES:
        await my_functions.send_by_channel(
            interaction.channel, f'Unknown platform "{platform}".'
        )
        return

    if position and (position < 1 or position > track_queue.queue_size):
        position = None

    tracks: list[Track] = await MUSIC_SOURCES[platform].search(
        content, interaction, shuffle, position, select_specific_search
    )

    if await client_is_disconnected(interaction) or len(tracks) == 0:
        return

    if shuffle and position:
        random.seed()
        random.shuffle(tracks)

    shuffle_queue: bool = shuffle and not position

    await track_queue.add_in_queue(
        interaction, tracks, position, content, shuffle_queue
    )

    await next_track(interaction, interaction.guild_id)


async def play_local(
    interaction: discord.Interaction[MyClient],
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

    player: GuildPlayer = interaction.client.get_player(interaction.guild_id)
    track_queue: TrackQueue = player.track_queue

    if position and (position < 1 or position > track_queue.queue_size):
        position = None

    message: discord.Message | None = await my_functions.send_by_channel(
        interaction.channel, "Loading local files...", permanent=True
    )
    tracks: list[Track] = await asyncio.to_thread(
        load_local_tracks, list_local_files(), interaction.user
    )

    if not tracks:
        await my_functions.edit_message(
            message, content="No local files found.", delete_after=10.0
        )
        return

    await my_functions.delete_msg(message)

    if await client_is_disconnected(interaction):
        return

    if shuffle and position:
        random.seed()
        random.shuffle(tracks)

    shuffle_queue: bool = shuffle and not position

    await track_queue.add_in_queue(
        interaction, tracks, position, "Local files", shuffle_queue
    )

    await next_track(interaction, interaction.guild_id)
