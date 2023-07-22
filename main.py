import discord

import globals_var
import my_functions
import secret_list
from globals_var import client_bot, tree, my_logger
import voice_gestion


async def msg_help(interaction: discord.Interaction):
    content = (
        "`clear`: Clear the queue.\n"
        "`disconnect`: Disconnect the bot.\n"
        "`help`: Display this message.\n"
        "`move position new_position`: Move the 'position' music to 'new_position'.\n"
        "`nowplaying`: Display the current music.\n"
        "`pause`: Pause the current music.\n"
        "`play`: Play <youtube url/playlist or search terms>.\n"
        "`play_default`: Play default musics of this server.\n"
        "`play_next (shuffle)`:Play this music after the current one. (can shuffle new music added)\n"
        "`play_shuffle`: Play music and shuffle queue.\n"
        "`queue (number)`: Display the queue.\n"
        "`remove begin (end)`: Remove `begin` music or [`begin`, `end`] musics.\n"
        "`resume`: Resume current music.\n"
        "`shuffle`: Shuffle musics.\n"
        "`skip`: Skip the current music.\n"
        "`stop`: Stop current music.\n"
    )

    await my_functions.send_by_channel(interaction.channel, content)


async def display_current_music(interaction: discord.Interaction):
    server = client_bot.get_server(interaction.guild_id)
    if not server.has_current_music_info():
        await my_functions.send_by_channel(interaction.channel, "No music.")
        return

    current_music_info = server.get_current_music_info()
    msg_content = (
        f"Playing {current_music_info.get_music().title}\n[Time] ["
        f"{current_music_info.get_audio().progress_str}"
        f" / {current_music_info.get_music().duration}]"
    )

    await my_functions.send_by_channel(interaction.channel, msg_content)


@client_bot.event
async def on_ready():
    guilds = []
    for guild in client_bot.guilds:
        guilds.append(guild.name)
    await client_bot.loop.create_task(tree.sync())

    my_logger.info(f"Logged in as {client_bot.user} to {guilds}.")


@client_bot.event
async def on_voice_state_update(member, before, after):
    voice_client: discord.VoiceClient = discord.utils.get(
        client_bot.voice_clients, guild=member.guild
    )
    if not voice_client:
        return

    if member == client_bot.user and before.channel and after.channel:
        if len(after.channel.members) == 1:
            client_bot.loop.create_task(
                my_functions.disconnect_bot(voice_client, member.guild.id)
            )
        else:
            voice_client.resume()
        return

    if (
        member != client_bot.user
        and before.channel
        and client_bot.user in before.channel.members
        and len(before.channel.members) == 1
    ):
        client_bot.loop.create_task(
            my_functions.disconnect_bot(voice_client, member.guild.id)
        )
        return

    if member == client_bot.user and before.channel and not after.channel:
        client_bot.loop.create_task(
            my_functions.disconnect_bot(voice_client, member.guild.id)
        )
        return


@tree.command(name="clear", description="Clear the queue.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    server = client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()
    await client_bot.loop.create_task(queue_musics.clear_queue(interaction))
    await client_bot.loop.create_task(
        my_functions.send_by_channel(interaction.channel, "The queue is cleared.")
    )


@tree.command(name="disconnect", description="Disconnect the bot.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(voice_gestion.disconnect(interaction))


@tree.command(name="help", description="Display commands.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(msg_help(interaction))


@tree.command(name="move", description="Move the 'position' music to 'new_position'")
async def self(interaction: discord.Interaction, position: int, new_position: int):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    server = client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()
    await client_bot.loop.create_task(
        queue_musics.move_music(interaction, position, new_position)
    )


@tree.command(name="nowplaying", description="Display the current music.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(display_current_music(interaction))


@tree.command(name="pause", description="Pause the current music.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(voice_gestion.pause_music(interaction))


@tree.command(name="play", description="Play youtube url/playlist or search terms.")
async def self(interaction: discord.Interaction, music: str, position: int = None):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, music, position=position)
    )


@tree.command(name="play_default", description="Play default musics of this server.")
async def self(
    interaction: discord.Interaction, shuffle: bool = False, position: int = None
):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if interaction.guild_id not in secret_list.default_musics:
        await client_bot.loop.create_task(
            my_functions.send_by_channel(
                interaction.channel, "No default music for this server"
            )
        )
        return

    await client_bot.loop.create_task(
        voice_gestion.play(
            interaction,
            secret_list.default_musics[interaction.guild_id],
            shuffle=shuffle,
            position=position,
        )
    )


@tree.command(
    name="play_next",
    description="Play this music after the current one. (can shuffle new music added)",
)
async def self(interaction: discord.Interaction, music: str, shuffle: bool = False):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, music, position=1, shuffle=shuffle)
    )


@tree.command(name="play_shuffle", description="Play and shuffle musics.")
async def self(interaction: discord.Interaction, music: str):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(
        voice_gestion.play(interaction, music, shuffle=True)
    )


@tree.command(name="queue", description="Display the queue.")
async def self(interaction: discord.Interaction, page: int = 1):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    server = client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()
    await client_bot.loop.create_task(queue_musics.get_queue(interaction, page))


@tree.command(
    name="remove", description="Remove 'begin' music or ['begin', 'end'] musics."
)
async def self(interaction: discord.Interaction, begin: int, end: int = None):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if begin < 1 or (end is not None and end < 1) or (end is not None and end < begin):
        await client_bot.loop.create_task(
            my_functions.send_by_channel(interaction.channel, "Number is incorrect!")
        )
        return

    if end is None:
        end = begin

    server = client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()

    await client_bot.loop.create_task(
        queue_musics.remove_musics(interaction, begin, end)
    )


@tree.command(name="resume", description="Resume the current music.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(voice_gestion.resume_music(interaction))


@tree.command(name="shuffle", description="Shuffle musics.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    server = client_bot.get_server(interaction.guild_id)
    queue_musics = server.get_queue_musics()
    await client_bot.loop.create_task(queue_musics.shuffle_queue(interaction))
    await client_bot.loop.create_task(
        my_functions.send_by_channel(interaction.channel, "The queue is shuffled.")
    )


@tree.command(
    name="skip", description="Skip the current music or first 'number' musics."
)
async def self(interaction: discord.Interaction, number: int = 1):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    if number < 1:
        await client_bot.loop.create_task(
            my_functions.send_by_channel(interaction.channel, "Numbers are incorrect!")
        )
        return

    await client_bot.loop.create_task(voice_gestion.skip_music(interaction, number))


@tree.command(name="stop", description="Stop music.")
async def self(interaction: discord.Interaction):
    await client_bot.loop.create_task(
        my_functions.send_by_interaction(interaction, "Request received")
    )
    await client_bot.loop.create_task(voice_gestion.stop_music(interaction))


def main():
    globals_var.initialize()
    client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
