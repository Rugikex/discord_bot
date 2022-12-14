import discord

import globals_var
import my_functions
import secret_list
from globals_var import current_music, client_bot, tree
import queue_gestion
import voice_gestion


async def msg_help(interaction: discord.Interaction):
    content = "`clear`: Clear the queue.\n" \
              "`disconnect`: Disconnect the bot.\n" \
              "`help`: Display this message.\n" \
              "`move position new_position`: Move the 'position' music to 'new_position'.\n" \
              "`nowplaying`: Display the current music.\n" \
              "`pause`: Pause the current music.\n" \
              "`play`: Play <youtube url/playlist or search terms>.\n" \
              "`play_default`: Play default musics of this server.\n" \
              "`play_next (shuffle)`:Play this music after the current one. (can shuffle new music added)\n" \
              "`play_shuffle`: Play music and shuffle queue.\n" \
              "`queue (number)`: Display the queue.\n" \
              "`remove begin (end)`: Remove `begin` music or [`begin`, `end`] musics.\n" \
              "`resume`: Resume current music.\n" \
              "`shuffle`: Shuffle musics.\n" \
              "`skip`: Skip the current music.\n" \
              "`stop`: Stop current music.\n"

    await my_functions.send(interaction, content)


async def display_current_music(interaction: discord.Interaction):
    if interaction.guild_id not in current_music:
        await my_functions.send(interaction, "No music.")
        return

    msg_content = f"Playing {current_music[interaction.guild_id]['music'].title}\n[Time] [" \
                  f"{current_music[interaction.guild_id]['audio'].progress_str}" \
                  f" / {current_music[interaction.guild_id]['music'].duration}]"

    await my_functions.send(interaction, msg_content)


@client_bot.event
async def on_ready():
    guilds = []
    for guild in client_bot.guilds:
        guilds.append(guild.name)
    await tree.sync()
    print(f'Logged in as {client_bot.user} to {guilds}.')


@client_bot.event
async def on_voice_state_update(member, before, after):
    voice_client: discord.VoiceClient = discord.utils.get(client_bot.voice_clients, guild=member.guild)
    if not voice_client:
        return

    if member == client_bot.user and before.channel and after.channel:
        if len(after.channel.members) == 1:
            await my_functions.disconnect_bot(voice_client, member.guild.id)
        else:
            voice_client.resume()
        return

    if member != client_bot.user and before.channel and client_bot.user in before.channel.members \
            and len(before.channel.members) == 1:
        await my_functions.disconnect_bot(voice_client, member.guild.id)
        return


@tree.command(name="clear", description="Clear the queue.")
async def self(interaction: discord.Interaction):
    await queue_gestion.clear_queue(interaction)
    await my_functions.send(interaction, 'The queue is cleared.')


@tree.command(name="disconnect", description="Disconnect the bot.")
async def self(interaction: discord.Interaction):
    await voice_gestion.disconnect(interaction)


@tree.command(name="help", description="Display commands.")
async def self(interaction: discord.Interaction):
    await msg_help(interaction)


@tree.command(name="move", description="Move the 'position' music to 'new_position'")
async def self(interaction: discord.Interaction, position: int, new_position: int):
    await queue_gestion.move_music(interaction, position, new_position)


@tree.command(name="nowplaying", description="Display the current music.")
async def self(interaction: discord.Interaction):
    await display_current_music(interaction)


@tree.command(name="pause", description="Pause the current music.")
async def self(interaction: discord.Interaction):
    await voice_gestion.pause_music(interaction)


@tree.command(name="play", description="Play youtube url/playlist or search terms.")
async def self(interaction: discord.Interaction, music: str, position: int = None):
    await voice_gestion.play(interaction, music, position=position)


@tree.command(name="play_default", description="Play default musics of this server.")
async def self(interaction: discord.Interaction, shuffle: bool = False, position: int = None):
    if interaction.guild_id not in secret_list.default_musics:
        await my_functions.send(interaction, "No default music for this server")
        return

    await voice_gestion.play(interaction, secret_list.default_musics[interaction.guild_id], shuffle=shuffle,
                             position=position)


@tree.command(name="play_next", description="Play this music after the current one. (can shuffle new music added)")
async def self(interaction: discord.Interaction, music: str, shuffle: bool = False):
    await voice_gestion.play(interaction, music, position=1, shuffle=shuffle)


@tree.command(name="play_shuffle", description="Play and shuffle musics.")
async def self(interaction: discord.Interaction, music: str):
    await voice_gestion.play(interaction, music, shuffle=True)


@tree.command(name="queue", description="Display the queue.")
async def self(interaction: discord.Interaction, page: int = 1):
    await queue_gestion.get_queue(interaction, page)


@tree.command(name="remove", description="Remove 'begin' music or ['begin', 'end'] musics.")
async def self(interaction: discord.Interaction, begin: int, end: int = None):
    if begin < 1 or (end is not None and end < 1) or (end is not None and end < begin):
        await my_functions.send(interaction, "Number is incorrect!")
        return

    if end is None:
        end = begin

    await queue_gestion.remove_musics(interaction, begin, end)


@tree.command(name="resume", description="Resume the current music.")
async def self(interaction: discord.Interaction):
    await voice_gestion.resume_music(interaction)


@tree.command(name="shuffle", description="Shuffle musics.")
async def self(interaction: discord.Interaction):
    await queue_gestion.shuffle_queue(interaction)
    await my_functions.send(interaction, 'The queue is shuffled.')


@tree.command(name="skip", description="Skip the current music or first 'number' musics.")
async def self(interaction: discord.Interaction, number: int = 1):
    if number < 1:
        await my_functions.send(interaction, "Numbers are incorrect!")
        return

    await voice_gestion.skip_music(interaction, number)


@tree.command(name="stop", description="Stop music.")
async def self(interaction: discord.Interaction):
    await voice_gestion.stop_music(interaction)


@tree.command(name="caca", description="C'est delicieux")
async def self(interaction: discord.Interaction):
    view = discord.ui.View()
    button1 = discord.ui.Button(label="Fraise")
    button2 = discord.ui.Button(label="Vanille", emoji='????', style=discord.ButtonStyle.success)
    view.add_item(button1)
    view.add_item(button2)

    async def button1_callback(interact: discord.Interaction):
        await interact.response.edit_message(content="Le caca sent la fraise")

    async def button2_callback(interact: discord.Interaction):
        await interact.response.edit_message(content="Le caca sent la vanille")

    button1.callback = button1_callback
    button2.callback = button2_callback

    await interaction.response.send_message("C'est vrai que c'est delicieux !", view=view)


def main():
    globals_var.initialize()
    client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
