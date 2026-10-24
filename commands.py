from __future__ import annotations
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands

from classes.music_source import MUSIC_SOURCES
from constants import MAX_DELETE_REPLIES_AFTER
import my_functions
import voice_gestion

if TYPE_CHECKING:
    from classes.current_track import CurrentTrack
    from classes.music_source import MusicSource
    from classes.my_client import MyClient
    from classes.guild_player import GuildPlayer
    from classes.track import Track
    from classes.track_queue import TrackQueue


PLATFORM_CHOICES: list[app_commands.Choice[str]] = [
    app_commands.Choice(name="YouTube", value="youtube"),
    app_commands.Choice(name="Local files", value="local"),
]


def add_commands(tree: app_commands.CommandTree) -> None:
    """Register every slash command and group of this module on the tree."""
    for value in globals().values():
        # Subcommands are registered through their group
        if (
            isinstance(value, (app_commands.Command, app_commands.Group))
            and value.parent is None
        ):
            tree.add_command(value)


async def msg_help(interaction: discord.Interaction[MyClient]) -> None:
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
        "`settings`: Display or change the settings of this server.\n"
        "`shuffle`: Shuffle tracks.\n"
        "`skip (number)`: Skip the current track or first 'number' tracks.\n"
        "`stop`: Stop current track.\n"
    )

    await my_functions.reply(interaction, content)


async def get_connected_player(
    interaction: discord.Interaction[MyClient],
) -> GuildPlayer | None:
    player: GuildPlayer | None = interaction.client.find_player(interaction.guild_id)
    if player is None:
        await my_functions.reply(
            interaction, "I'm not connected to this server.", private=True
        )
    return player


async def display_current_track(interaction: discord.Interaction[MyClient]) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    if player.current_track is None:
        await my_functions.reply(interaction, "No track.", private=True)
        return

    current_track: CurrentTrack = player.current_track
    msg_content: str = (
        f"Playing {current_track.track.title}\n[Time] ["
        f"{current_track.audio.progress_str}"
        f" / {current_track.track.duration}]"
    )

    await my_functions.reply(interaction, msg_content)


# The blacklist and the "thinking..." message are handled by MyCommandTree


@app_commands.command(
    name="add_local_tracks", description="Add all local files in the queue."
)
@app_commands.guild_only()
async def cmd_add_local_tracks(
    interaction: discord.Interaction[MyClient],
    shuffle: bool = False,
    position: int | None = None,
) -> None:
    await voice_gestion.play_local(interaction, shuffle=shuffle, position=position)


@app_commands.command(name="clear", description="Clear the queue.")
@app_commands.guild_only()
async def cmd_clear(interaction: discord.Interaction[MyClient]) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue
    if await track_queue.clear_queue(interaction):
        await my_functions.reply(interaction, "The queue is cleared.")


@app_commands.command(name="disconnect", description="Disconnect the bot.")
@app_commands.guild_only()
async def cmd_disconnect(interaction: discord.Interaction[MyClient]) -> None:
    await voice_gestion.disconnect(interaction)


@app_commands.command(name="help", description="Display commands.")
@app_commands.guild_only()
async def cmd_help(interaction: discord.Interaction[MyClient]) -> None:
    await msg_help(interaction)


@app_commands.command(name="loop", description="Loop or unloop the current track.")
@app_commands.guild_only()
async def cmd_loop(interaction: discord.Interaction[MyClient]) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    player.switch_looping(interaction.user.mention)
    await my_functions.reply(
        interaction, f"Looping is {'enabled' if player.is_looping else 'disabled'}."
    )

    if player.current_track is not None:
        track: Track = player.current_track.track
        embed, _ = MUSIC_SOURCES[track.origin].create_embed(
            track, player.loop_requester
        )
        if player.current_track.message is not None:
            await my_functions.edit_message(
                player.current_track.message, "", embed=embed
            )
        else:
            message = await my_functions.send_by_channel(
                interaction.channel, "", permanent=True, embed=embed
            )
            player.current_track.update(
                player.current_track.track, message, player.current_track.audio
            )


@app_commands.command(
    name="move", description="Move the 'position' track to 'new_position'"
)
@app_commands.guild_only()
async def cmd_move(
    interaction: discord.Interaction[MyClient], position: int, new_position: int
) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue
    await track_queue.move_track(interaction, position, new_position)


@app_commands.command(name="nowplaying", description="Display the current track.")
@app_commands.guild_only()
async def cmd_nowplaying(interaction: discord.Interaction[MyClient]) -> None:
    await display_current_track(interaction)


@app_commands.command(name="pause", description="Pause the current track.")
@app_commands.guild_only()
async def cmd_pause(interaction: discord.Interaction[MyClient]) -> None:
    await voice_gestion.pause_track(interaction)


@app_commands.command(name="play", description="Play url/playlist or search terms.")
@app_commands.choices(platform=PLATFORM_CHOICES)
@app_commands.guild_only()
async def cmd_play(
    interaction: discord.Interaction[MyClient],
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
    link: str | None = default_tracks.get("link")
    if not link:
        await my_functions.reply(
            interaction, "No default track for this server", private=True
        )
        return

    await voice_gestion.play(
        interaction,
        link,
        default_tracks.get("platform"),
        shuffle=shuffle,
        position=position,
    )


@app_commands.command(
    name="play_next",
    description="Play this track after the current one. (can shuffle new track added)",
)
@app_commands.choices(platform=PLATFORM_CHOICES)
@app_commands.guild_only()
async def cmd_play_next(
    interaction: discord.Interaction[MyClient],
    track: str,
    platform: app_commands.Choice[str] | None = None,
    shuffle: bool = False,
) -> None:
    await voice_gestion.play(interaction, track, platform, position=1, shuffle=shuffle)


@app_commands.command(name="play_shuffle", description="Play and shuffle tracks.")
@app_commands.choices(platform=PLATFORM_CHOICES)
@app_commands.guild_only()
async def cmd_play_shuffle(
    interaction: discord.Interaction[MyClient],
    track: str,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    await voice_gestion.play(interaction, track, platform, shuffle=True)


@app_commands.command(name="queue", description="Display the queue.")
@app_commands.guild_only()
async def cmd_queue(interaction: discord.Interaction[MyClient], page: int = 1) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue
    await track_queue.get_queue(interaction, page)


@app_commands.command(
    name="remove", description="Remove 'begin' track or ['begin', 'end'] tracks."
)
@app_commands.guild_only()
async def cmd_remove(
    interaction: discord.Interaction[MyClient], begin: int, end: int | None = None
) -> None:
    if begin < 1 or (end is not None and end < 1) or (end is not None and end < begin):
        await my_functions.reply(interaction, "Number is incorrect!", private=True)
        return

    if end is None:
        end = begin

    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue

    await track_queue.remove_tracks(interaction, begin, end)


@app_commands.command(name="resume", description="Resume the current track.")
@app_commands.guild_only()
async def cmd_resume(interaction: discord.Interaction[MyClient]) -> None:
    await voice_gestion.resume_track(interaction)


@app_commands.command(name="shuffle", description="Shuffle tracks.")
@app_commands.guild_only()
async def cmd_shuffle(interaction: discord.Interaction[MyClient]) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue
    if await track_queue.shuffle_queue(interaction):
        await my_functions.reply(interaction, "The queue is shuffled.")


@app_commands.command(
    name="skip", description="Skip the current track or first 'number' tracks."
)
@app_commands.guild_only()
async def cmd_skip(interaction: discord.Interaction[MyClient], number: int = 1) -> None:
    if number < 1:
        await my_functions.reply(interaction, "Numbers are incorrect!", private=True)
        return

    await voice_gestion.skip_track(interaction, number)


@app_commands.command(name="stop", description="Stop track.")
@app_commands.guild_only()
async def cmd_stop(interaction: discord.Interaction[MyClient]) -> None:
    player: GuildPlayer | None = await get_connected_player(interaction)
    if player is None:
        return
    track_queue: TrackQueue = player.track_queue
    await track_queue.stop_track(interaction)


settings_group: app_commands.Group = app_commands.Group(
    name="settings",
    description="Display or change the settings of this server.",
    guild_only=True,
    # Server admins can change who sees it in Server Settings > Integrations
    default_permissions=discord.Permissions(manage_guild=True),
)


def format_delay_setting(seconds: int) -> str:
    return "kept" if seconds == 0 else f"deleted after {seconds} s"


def format_track_setting(value: dict[str, str | None] | None) -> str:
    if not value or not value.get("link"):
        return "None"
    return f"`{value['link']}` ({value.get('platform') or 'default platform'})"


@settings_group.command(name="show", description="Display the settings.")
async def cmd_settings_show(interaction: discord.Interaction[MyClient]) -> None:
    settings: dict[str, Any] = interaction.client.load_settings(interaction.guild_id)
    await my_functions.reply(
        interaction,
        f"**Default platform:** {settings['default_platform']}\n"
        f"**Default tracks:** {format_track_setting(settings['default_tracks'])}\n"
        f"**Welcome track:** {format_track_setting(settings['welcome_track'])}\n"
        "**Delete replies after:** "
        f"{format_delay_setting(settings['delete_replies_after'])}",
        private=True,
    )


@settings_group.command(
    name="default_platform", description="Platform used when none is chosen."
)
@app_commands.choices(platform=PLATFORM_CHOICES)
async def cmd_settings_default_platform(
    interaction: discord.Interaction[MyClient], platform: app_commands.Choice[str]
) -> None:
    interaction.client.update_setting(
        interaction.guild_id, "default_platform", platform.value
    )
    await my_functions.reply(
        interaction, f"Default platform set to {platform.name}.", private=True
    )


@settings_group.command(
    name="default_tracks",
    description="Tracks played by /play_default (without link to remove them).",
)
@app_commands.describe(link="Url, playlist or search terms.")
@app_commands.choices(platform=PLATFORM_CHOICES)
async def cmd_settings_default_tracks(
    interaction: discord.Interaction[MyClient],
    link: str | None = None,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    interaction.client.update_setting(
        interaction.guild_id,
        "default_tracks",
        {"link": link, "platform": platform.value if platform else None},
    )
    await my_functions.reply(
        interaction,
        (
            "Default tracks removed."
            if link is None
            else f"Default tracks set to `{link}`."
        ),
        private=True,
    )


@settings_group.command(
    name="welcome_track",
    description="Track played when the bot joins a channel (without link to disable).",
)
@app_commands.describe(link="Url of one track, or path of a local file (music/...).")
@app_commands.choices(platform=PLATFORM_CHOICES)
async def cmd_settings_welcome_track(
    interaction: discord.Interaction[MyClient],
    link: str | None = None,
    platform: app_commands.Choice[str] | None = None,
) -> None:
    if link is None:
        interaction.client.update_setting(
            interaction.guild_id, "welcome_track", {"link": None, "platform": None}
        )
        await my_functions.reply(interaction, "Welcome track disabled.", private=True)
        return

    platform_value: str = (
        platform.value
        if platform
        else interaction.client.load_settings(interaction.guild_id)["default_platform"]
    )
    music_source: MusicSource | None = MUSIC_SOURCES.get(platform_value)
    # Check the link now rather than failing silently at the next connection
    track: Track | None = (
        await music_source.get_track(link, interaction.user) if music_source else None
    )
    if track is None:
        await my_functions.reply(
            interaction, f"Can't find a single track for `{link}`.", private=True
        )
        return

    interaction.client.update_setting(
        interaction.guild_id,
        "welcome_track",
        {"link": link, "platform": platform_value},
    )
    await my_functions.reply(
        interaction,
        f'Welcome track set to "{track}" (from the next connection).',
        private=True,
    )


@settings_group.command(
    name="delete_replies_after",
    description="Seconds before answers to commands are deleted (0 to keep them).",
)
async def cmd_settings_delete_replies_after(
    interaction: discord.Interaction[MyClient],
    seconds: app_commands.Range[int, 0, MAX_DELETE_REPLIES_AFTER],
) -> None:
    interaction.client.update_setting(
        interaction.guild_id, "delete_replies_after", seconds
    )
    await my_functions.reply(
        interaction,
        f"Answers to commands: {format_delay_setting(seconds)}.",
        private=True,
    )
