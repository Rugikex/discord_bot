from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from classes.music_source import MUSIC_SOURCES
import my_functions
import voice_gestion

if TYPE_CHECKING:
    from classes.current_track import CurrentTrack
    from classes.my_client import MyClient
    from classes.server import Server
    from classes.track import Track
    from classes.track_queue import TrackQueue


def add_commands(tree: app_commands.CommandTree) -> None:
    """Register every slash command of this module on the tree."""
    for value in globals().values():
        if isinstance(value, app_commands.Command):
            tree.add_command(value)


async def msg_help(interaction: discord.Interaction) -> None:
    content: str = (
        "`add_local_tracks (shuffle) (position)`: Add all local files in the queue.\n"
        "`clear`: Clear the queue.\n"
        "`disconnect`: Disconnect the bot.\n"
        "`help`: Display this message.\n"
        "`loop`: Loop or unloop the current track.\n"
        "`move position new_position`: Move the 'position' track to 'new_position'.\n"
        "`nowplaying`: Display the current track.\n"
        "`pause`: Pause the current track.\n"
        "`play`: Play <youtube url/playlist or search terms>.\n"
        "`play_default`: Play default tracks of this server.\n"
        "`play_next (shuffle)`: Play this track after the current one. (can shuffle new track added)\n"
        "`play_shuffle`: Play track and shuffle queue.\n"
        "`queue (number)`: Display the queue.\n"
        "`remove begin (end)`: Remove `begin` track or [`begin`, `end`] tracks.\n"
        "`resume`: Resume current track.\n"
        "`shuffle`: Shuffle tracks.\n"
        "`skip (number)`: Skip the current track or first 'number' tracks.\n"
        "`stop`: Stop current track.\n"
    )

    await my_functions.send_by_channel(interaction.channel, content)


async def get_connected_server(
    interaction: discord.Interaction[MyClient],
) -> Server | None:
    server: Server | None = interaction.client.find_server(interaction.guild_id)
    if server is None:
        await my_functions.send_by_channel(
            interaction.channel, "I'm not connected to this server."
        )
    return server


async def display_current_track(interaction: discord.Interaction) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    if server.current_track is None:
        await my_functions.send_by_channel(interaction.channel, "No track.")
        return

    current_track: CurrentTrack = server.current_track
    msg_content: str = (
        f"Playing {current_track.track.title}\n[Time] ["
        f"{current_track.audio.progress_str}"
        f" / {current_track.track.duration}]"
    )

    await my_functions.send_by_channel(interaction.channel, msg_content)


# The blacklist and "Request received" are handled by MyCommandTree.interaction_check


@app_commands.command(
    name="add_local_tracks", description="Add all local files in the queue."
)
@app_commands.guild_only()
async def cmd_add_local_tracks(
    interaction: discord.Interaction, shuffle: bool = False, position: int | None = None
) -> None:
    await voice_gestion.play_local(interaction, shuffle=shuffle, position=position)


@app_commands.command(name="clear", description="Clear the queue.")
@app_commands.guild_only()
async def cmd_clear(interaction: discord.Interaction) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue
    if await track_queue.clear_queue(interaction):
        await my_functions.send_by_channel(interaction.channel, "The queue is cleared.")


@app_commands.command(name="disconnect", description="Disconnect the bot.")
@app_commands.guild_only()
async def cmd_disconnect(interaction: discord.Interaction) -> None:
    await voice_gestion.disconnect(interaction)


@app_commands.command(name="help", description="Display commands.")
@app_commands.guild_only()
async def cmd_help(interaction: discord.Interaction) -> None:
    await msg_help(interaction)


@app_commands.command(name="loop", description="Loop or unloop the current track.")
@app_commands.guild_only()
async def cmd_loop(interaction: discord.Interaction) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    server.switch_looping(interaction.user.mention)
    await my_functions.send_by_channel(
        interaction.channel,
        f"Looping is {'enabled' if server.is_looping else 'disabled'}.",
    )

    if server.current_track is not None:
        track: Track = server.current_track.track
        embed, _ = MUSIC_SOURCES[track.origin].create_embed(
            track, server.loop_requester
        )
        if server.current_track.message is not None:
            await my_functions.edit_message(
                server.current_track.message, "", embed=embed
            )
        else:
            message = await my_functions.send_by_channel(
                interaction.channel, "", permanent=True, embed=embed
            )
            server.current_track.update(
                server.current_track.track, message, server.current_track.audio
            )


@app_commands.command(
    name="move", description="Move the 'position' track to 'new_position'"
)
@app_commands.guild_only()
async def cmd_move(
    interaction: discord.Interaction, position: int, new_position: int
) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue
    await track_queue.move_track(interaction, position, new_position)


@app_commands.command(name="nowplaying", description="Display the current track.")
@app_commands.guild_only()
async def cmd_nowplaying(interaction: discord.Interaction) -> None:
    await display_current_track(interaction)


@app_commands.command(name="pause", description="Pause the current track.")
@app_commands.guild_only()
async def cmd_pause(interaction: discord.Interaction) -> None:
    await voice_gestion.pause_track(interaction)


@app_commands.command(name="play", description="Play url/playlist or search terms.")
@app_commands.choices(
    platform=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Local files", value="local"),
    ]
)
@app_commands.guild_only()
async def cmd_play(
    interaction: discord.Interaction,
    track: str,
    platform: app_commands.Choice[str] | None = None,
    position: int | None = None,
) -> None:
    await voice_gestion.play(interaction, track, platform, position=position)


@app_commands.command(
    name="play_default", description="Play default tracks of this server."
)
@app_commands.guild_only()
async def cmd_play_default(
    interaction: discord.Interaction[MyClient],
    shuffle: bool = False,
    position: int | None = None,
) -> None:
    # Settings are read from the file: the bot may not be connected yet
    default_tracks: dict[str, str | None] = interaction.client.load_settings(
        interaction.guild_id
    )["default_tracks"]
    if not default_tracks.get("link"):
        await my_functions.send_by_channel(
            interaction.channel, "No default track for this server"
        )
        return

    await voice_gestion.play(
        interaction,
        default_tracks["link"],
        default_tracks.get("platform"),
        shuffle=shuffle,
        position=position,
    )


@app_commands.command(
    name="play_next",
    description="Play this track after the current one. (can shuffle new track added)",
)
@app_commands.choices(
    platform=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Local files", value="local"),
    ]
)
@app_commands.guild_only()
async def cmd_play_next(
    interaction: discord.Interaction,
    track: str,
    platform: app_commands.Choice[str] | None = None,
    shuffle: bool = False,
) -> None:
    await voice_gestion.play(interaction, track, platform, position=1, shuffle=shuffle)


@app_commands.command(name="play_shuffle", description="Play and shuffle tracks.")
@app_commands.choices(
    platform=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="Local files", value="local"),
    ]
)
@app_commands.guild_only()
async def cmd_play_shuffle(
    interaction: discord.Interaction,
    track: str,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    await voice_gestion.play(interaction, track, platform, shuffle=True)


@app_commands.command(name="queue", description="Display the queue.")
@app_commands.guild_only()
async def cmd_queue(interaction: discord.Interaction, page: int = 1) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue
    await track_queue.get_queue(interaction, page)


@app_commands.command(
    name="remove", description="Remove 'begin' track or ['begin', 'end'] tracks."
)
@app_commands.guild_only()
async def cmd_remove(
    interaction: discord.Interaction, begin: int, end: int | None = None
) -> None:
    if begin < 1 or (end is not None and end < 1) or (end is not None and end < begin):
        await my_functions.send_by_channel(interaction.channel, "Number is incorrect!")
        return

    if end is None:
        end = begin

    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue

    await track_queue.remove_tracks(interaction, begin, end)


@app_commands.command(name="resume", description="Resume the current track.")
@app_commands.guild_only()
async def cmd_resume(interaction: discord.Interaction) -> None:
    await voice_gestion.resume_track(interaction)


@app_commands.command(name="shuffle", description="Shuffle tracks.")
@app_commands.guild_only()
async def cmd_shuffle(interaction: discord.Interaction) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue
    if await track_queue.shuffle_queue(interaction):
        await my_functions.send_by_channel(
            interaction.channel, "The queue is shuffled."
        )


@app_commands.command(
    name="skip", description="Skip the current track or first 'number' tracks."
)
@app_commands.guild_only()
async def cmd_skip(interaction: discord.Interaction, number: int = 1) -> None:
    if number < 1:
        await my_functions.send_by_channel(
            interaction.channel, "Numbers are incorrect!"
        )
        return

    await voice_gestion.skip_track(interaction, number)


@app_commands.command(name="stop", description="Stop track.")
@app_commands.guild_only()
async def cmd_stop(interaction: discord.Interaction) -> None:
    server: Server | None = await get_connected_server(interaction)
    if server is None:
        return
    track_queue: TrackQueue = server.track_queue
    await track_queue.stop_track(interaction)
