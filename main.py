from __future__ import annotations
from typing import TYPE_CHECKING

import discord

import globals_var
import my_functions
import secret_list
from globals_var import client_bot, tree, my_logger
import voice_gestion

if TYPE_CHECKING:
    from classes.server import Server
    from classes.track import Track
    from classes.track_queue import TrackQueue


async def msg_help(interaction: discord.Interaction) -> None:
    content: str = (
        "`clear`: Clear the queue.\n"
        "`disconnect`: Disconnect the bot.\n"
        "`help`: Display this message.\n"
        "`move position new_position`: Move the 'position' track to 'new_position'.\n"
        "`nowplaying`: Display the current track.\n"
        "`pause`: Pause the current track.\n"
        "`play`: Play <youtube url/playlist or search terms>.\n"
        "`play_default`: Play default tracks of this server.\n"
        "`play_next (shuffle)`:Play this track after the current one. (can shuffle new track added)\n"
        "`play_shuffle`: Play track and shuffle queue.\n"
        "`queue (number)`: Display the queue.\n"
        "`remove begin (end)`: Remove `begin` track or [`begin`, `end`] tracks.\n"
        "`resume`: Resume current track.\n"
        "`shuffle`: Shuffle tracks.\n"
        "`skip`: Skip the current track.\n"
        "`stop`: Stop current track.\n"
    )

    await my_functions.send_by_channel(interaction.channel, content)


async def display_current_track(interaction: discord.Interaction) -> None:
    server: Server = client_bot.get_server(interaction.guild_id)
    if server.current_track is None:
        await my_functions.send_by_channel(interaction.channel, "No track.")
        return

    current_track: Track = server.current_track
    msg_content: str = (
        f"Playing {current_track.track.title}\n[Time] ["
        f"{current_track.audio.progress_str}"
        f" / {current_track.track.duration}]"
    )

    await my_functions.send_by_channel(interaction.channel, msg_content)


@client_bot.event
async def on_ready() -> None:
    guilds: list[str] = []
    for guild in client_bot.guilds:
        guilds.append(guild.name)
    await client_bot.loop.create_task(tree.sync())

    my_logger.info("Logged in as %s to %s.", client_bot.user, guilds)


@client_bot.event
async def on_voice_state_update(member, before, after) -> None:
    """Disconnect the bot if alone in a voice channel or if kicked."""
    voice_client: discord.VoiceClient = discord.utils.get(
        client_bot.voice_clients, guild=member.guild
    )
    if voice_client is None or before.channel is None:
        return

    if not client_bot.server_exists(member.guild.id):
        return

    if (
        member != client_bot.user
        and client_bot.user in before.channel.members
        and len(before.channel.members) == 1
    ):
        client_bot.loop.create_task(
            my_functions.disconnect_bot(voice_client, member.guild.id)
        )
        return

    if (
        member == client_bot.user
        and after.channel
        and before.channel is not after.channel
    ):
        if len(after.channel.members) == 1:
            client_bot.loop.create_task(
                my_functions.disconnect_bot(voice_client, member.guild.id)
            )
        else:
            voice_client.resume()
        return

    if (
        member == client_bot.user
        and not after.channel
        and len(before.channel.members) != 0
    ):
        client_bot.loop.create_task(
            my_functions.disconnect_bot(voice_client, member.guild.id)
        )
        return


@tree.command(name="clear", description="Clear the queue.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue
    await client_bot.loop.create_task(track_queue.clear_queue(interaction))
    await client_bot.loop.create_task(
        my_functions.send_by_channel(interaction.channel, "The queue is cleared.")
    )


@tree.command(name="disconnect", description="Disconnect the bot.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(voice_gestion.disconnect(interaction))


@tree.command(name="help", description="Display commands.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(msg_help(interaction))


@tree.command(name="loop", description="Loop or unloop the current track.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return

    server: Server = client_bot.get_server(interaction.guild_id)
    server.switch_looping(interaction.user.mention)
    await client_bot.loop.create_task(
        my_functions.send_by_channel(
            interaction.channel,
            f"Looping is {'enabled' if server.is_looping else 'disabled'}.",
        )
    )

    if server.current_track is not None:
        track: Track = server.current_track.track
        embed, _ = my_functions.create_embed(track, server.loop_requester)
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


@tree.command(name="move", description="Move the 'position' track to 'new_position'")
async def self(
    interaction: discord.Interaction, position: int, new_position: int
) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue
    await client_bot.loop.create_task(
        track_queue.move_track(interaction, position, new_position)
    )


@tree.command(name="nowplaying", description="Display the current track.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(display_current_track(interaction))


@tree.command(name="pause", description="Pause the current track.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(voice_gestion.pause_track(interaction))


@tree.command(name="play", description="Play youtube url/playlist or search terms.")
async def self(
    interaction: discord.Interaction, track: str, position: int | None = None
) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, track, position=position)
    )


@tree.command(name="play_default", description="Play default tracks of this server.")
async def self(
    interaction: discord.Interaction, shuffle: bool = False, position: int | None = None
) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    if interaction.guild_id not in secret_list.default_tracks:
        await client_bot.loop.create_task(
            my_functions.send_by_channel(
                interaction.channel, "No default track for this server"
            )
        )
        return

    await client_bot.loop.create_task(
        voice_gestion.play(
            interaction,
            secret_list.default_tracks[interaction.guild_id],
            shuffle=shuffle,
            position=position,
        )
    )


@tree.command(
    name="play_next",
    description="Play this track after the current one. (can shuffle new track added)",
)
async def self(
    interaction: discord.Interaction, track: str, shuffle: bool = False
) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, track, position=1, shuffle=shuffle)
    )


@tree.command(name="play_shuffle", description="Play and shuffle tracks.")
async def self(interaction: discord.Interaction, track: str) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, track, shuffle=True)
    )


@tree.command(name="queue", description="Display the queue.")
async def self(interaction: discord.Interaction, page: int = 1) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue = server.track_queue
    await client_bot.loop.create_task(track_queue.get_queue(interaction, page))


@tree.command(
    name="remove", description="Remove 'begin' track or ['begin', 'end'] tracks."
)
async def self(interaction: discord.Interaction, begin: int, end: int = None) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    if begin < 1 or (end is not None and end < 1) or (end is not None and end < begin):
        await client_bot.loop.create_task(
            my_functions.send_by_channel(interaction.channel, "Number is incorrect!")
        )
        return

    if end is None:
        end = begin

    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue

    await client_bot.loop.create_task(
        track_queue.remove_tracks(interaction, begin, end)
    )


@tree.command(name="resume", description="Resume the current track.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    await client_bot.loop.create_task(voice_gestion.resume_track(interaction))


@tree.command(name="shuffle", description="Shuffle tracks.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue
    await client_bot.loop.create_task(track_queue.shuffle_queue(interaction))
    await client_bot.loop.create_task(
        my_functions.send_by_channel(interaction.channel, "The queue is shuffled.")
    )


@tree.command(
    name="skip", description="Skip the current track or first 'number' tracks."
)
async def self(interaction: discord.Interaction, number: int = 1) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return
    if number < 1:
        await client_bot.loop.create_task(
            my_functions.send_by_channel(interaction.channel, "Numbers are incorrect!")
        )
        return

    await client_bot.loop.create_task(voice_gestion.skip_track(interaction, number))


@tree.command(name="stop", description="Stop track.")
async def self(interaction: discord.Interaction) -> None:
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if my_functions.user_is_blacklisted(interaction.user.id):
        await client_bot.loop.create_task(
            my_functions.send_by_interaction(interaction, globals_var.msg_blacklist)
        )
        return

    server: Server = client_bot.get_server(interaction.guild_id)
    track_queue: TrackQueue = server.track_queue
    await client_bot.loop.create_task(track_queue.stop_track(interaction))


def main():
    globals_var.initialize()
    client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
