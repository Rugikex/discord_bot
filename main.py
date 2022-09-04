import datetime
import re
import discord

import globals_var
import my_message
from globals_var import prefix, current_music, client_bot, specifics_searches, queues_musics, tree
import queue_gestion
import voice_gestion


async def msg_help(message: discord.Message):
    content = f"`{prefix}help` or `{prefix}h`: Display this message.\n" \
              f"`{prefix}play` or `{prefix}p`: Play music with <youtube url/playlist or search terms>.\n" \
              f"`{prefix}playshuffle` or `{prefix}ps`: Play music and shuffle queue.\n" \
              f"`{prefix}shuffle`: Shuffle queue.\n" \
              f"`{prefix}nowplaying` or `{prefix}np`: Display current playing music\n" \
              f"`{prefix}queue (number)`: Display queue.\n" \
              f"`{prefix}skip (number)` or `{prefix}s (number)`: Skip 1 or `number` music(s).\n" \
              f"`{prefix}clear`: Clear queue.\n" \
              f"`{prefix}stop`: Stop current music.\n" \
              f"`{prefix}resume`: Resume current music.\n" \
              f"`{prefix}quit`: Disconnect the bot.\n"

    await my_message.send(message, content)


async def display_current_music(interaction: discord.Interaction):
    if interaction.guild_id not in current_music:
        return

    msg_content = f"Playing {current_music[interaction.guild_id]['music'].title}\n[Time] ["

    if current_music[interaction.guild_id]['is_paused']:
        msg_content += f"{str(current_music[interaction.guild_id]['time_spent']).split('.')[0]}"
    else:
        duration = datetime.datetime.now() + current_music[interaction.guild_id]['time_spent'] \
                   - current_music[interaction.guild_id]['start_time']
        duration_without_ms = str(duration).split('.')[0]
        msg_content += f"{duration_without_ms}"

    msg_content += f" / {current_music[interaction.guild_id]['music'].duration}]"
    await my_message.send(interaction, msg_content)


@client_bot.event
async def on_ready():
    guilds = []
    for guild in client_bot.guilds:
        guilds.append(guild.name)
    await tree.sync()
    print(f'Logged in as {client_bot.user} to {guilds}.')


@client_bot.event
async def on_message(message: discord.Message):
    if message.author == client_bot.user:
        return

    if not message.content.startswith(prefix):
        return

    # FIXME old, now with new reactions
    if message.guild.id in specifics_searches and \
            message.author == specifics_searches[message.guild.id]['user']:
        can_exec = True
        try:
            number = int("42")
        except ValueError:
            can_exec = False

        if 'message' not in globals_var.specifics_searches[message.guild.id]:
            await my_message.send(message, 'Wait loading please.', delete_after=3)
            return

        if can_exec:
            await voice_gestion.select_specific_search(message, number)
            return


@client_bot.event
async def on_reaction_add(reaction, user):
    if user == client_bot.user:
        return

    print("cacaOUI")

    if user.guild.id in queues_musics and reaction.message.author == globals_var.client_bot.user \
            and reaction.message.content.startswith("Queue list(page "):
        if reaction.emoji not in globals_var.reactions_queue:
            return

        page = int(re.search("Queue list\(page (.*)\):", reaction.message.content).group(1))
        if page == 1 and reaction.emoji == globals_var.reactions_queue[0]:
            return

        if not queues_musics[reaction.message.guild.id][page * 10:] \
                and reaction.emoji == globals_var.reactions_queue[1]:
            return

        if reaction.emoji == globals_var.reactions_queue[0]:
            page -= 1
        else:
            page += 1

        await reaction.message.edit(content=queue_gestion.message_queue(reaction.message, page))
        await reaction.message.clear_reactions()

        await queue_gestion.reactions_on_message_queue(reaction.message, page)

        return

    if user.guild.id in globals_var.specifics_searches:
        if reaction.message != globals_var.specifics_searches[user.guild.id]['message']:
            return

        if user != globals_var.specifics_searches[user.guild.id]['user']:
            return

        if user.voice is None:
            await my_message.send(reaction.message, 'You have to be connected to a voice channel in this server!',
                                  delete_after=10)
            return

        if reaction.emoji not in \
                globals_var.reactions_song[:len(globals_var.specifics_searches[user.guild.id]['searches']) + 1]:
            return

        await voice_gestion.select_specific_search(reaction.message,
                                                   globals_var.reactions_song.index(reaction.emoji) + 1)


@tree.command(name="clear", description="Clear the queue")
async def self(interaction: discord.Interaction):
    await queue_gestion.clear_queue(interaction)


@tree.command(name="nowplaying", description="Display the current music")
async def self(interaction: discord.Interaction):
    await display_current_music(interaction)


@tree.command(name="disconnect", description="Disconnect the bot")
async def self(interaction: discord.Interaction):
    await voice_gestion.disconnect(interaction)


@tree.command(name="pause", description="Pause the current music")
async def self(interaction: discord.Interaction):
    await voice_gestion.pause_music(interaction)


@tree.command(name="play", description="Play youtube url/playlist or search terms")
async def self(interaction: discord.Interaction, music: str):
    await voice_gestion.play(interaction, music)


@tree.command(name="play_shuffle", description="Play and shuffle musics")
async def self(interaction: discord.Interaction, music: str):
    await voice_gestion.play(interaction, music, shuffle=True)


@tree.command(name="queue", description="Display the queue")
async def self(interaction: discord.Interaction, page: int = 1):
    await queue_gestion.get_queue(interaction, page)


@tree.command(name="resume", description="Resume the current music")
async def self(interaction: discord.Interaction):
    await voice_gestion.resume_music(interaction)


@tree.command(name="shuffle", description="Shuffle musics")
async def self(interaction: discord.Interaction):
    await queue_gestion.shuffle_queue(interaction)


@tree.command(name="skip", description="Skip the current music")
async def self(interaction: discord.Interaction):
    await voice_gestion.skip_music(interaction)


@tree.command(name="stop", description="Stop music")
async def self(interaction: discord.Interaction):
    await voice_gestion.stop_music(interaction)


@tree.command(name="caca", description="C'est delicieux")
async def self(interaction: discord.Interaction):
    if __name__ == '__main__':
        await interaction.response.send_message("C'est vrai que c'est delicieux !")


def main():
    globals_var.initialize()
    client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
