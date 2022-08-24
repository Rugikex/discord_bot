import datetime
import re
import discord

import globals_var
from globals_var import prefix, current_music, client_bot, specifics_searches, queues_musics
import queue_gestion
import voice_gestion


async def msg_help(message: discord.Message):
    content = f"`{prefix}help` or `{prefix}h`: Display this message.\n" \
              f"`{prefix}play` or `{prefix}p`: Play music with <youtube url/playlist or search terms>.\n" \
              f"`{prefix}playshuffle` or `{prefix}ps`: Play music and shuffle queue.\n" \
              f"`{prefix}shuffle`: Shuffle queue.\n" \
              f"`{prefix}nowplaying` or `{prefix}np`: Display message about the current playing music" \
              f"`{prefix}skip` or `{prefix}s`: Skip current music.\n" \
              f"`{prefix}clear`: Clear queue.\n" \
              f"`{prefix}stop`: Stop current music.\n" \
              f"`{prefix}resume`: Resume current music.\n" \
              f"`{prefix}quit`: Disconnect the bot.\n"

    await message.channel.send(content)


async def display_current_music(message: discord.Message):
    if message.guild.id not in current_music:
        return

    msg_content = f"Playing {current_music[message.guild.id]['music'].title}\n[Time] "

    if current_music[message.guild.id]['is_paused']:
        msg_content += f"({str(current_music[message.guild.id]['time_spent']).split('.')[0]}"
    else:
        duration = datetime.datetime.now() + current_music[message.guild.id]['time_spent']\
                   - current_music[message.guild.id]['start_time']
        duration_without_ms = str(duration).split('.')[0]
        msg_content += f"({duration_without_ms}"

    msg_content += f" / {current_music[message.guild.id]['music'].duration})"
    await message.channel.send(msg_content)


@client_bot.event
async def on_ready():
    guilds = []
    for guild in client_bot.guilds:
        guilds.append(guild.name)
    print(f'Logged in as {client_bot.user} to {guilds}.')


@client_bot.event
async def on_message(message: discord.Message):
    if message.author == client_bot.user:
        return

    if not message.content.startswith(prefix):
        return

    content = str(message.content[len(prefix):])
    if len(content) == 0:
        await message.channel.send(f'Need help? Check {prefix}help.')
        return

    if message.guild.id in specifics_searches and \
            message.author == specifics_searches[message.guild.id]['user']:
        try:
            number = int(content)
        except ValueError:
            return

        await voice_gestion.select_specific_search(message, number)
        return

    if content == 'clear':
        await queue_gestion.clear_queue(message)
        return

    if content == 'help' or content == 'h':
        await msg_help(message)
        return

    if content == 'nowplaying' or content == 'np':
        await display_current_music(message)
        return

    if content == 'queue':
        await queue_gestion.get_queue(message, 1)
        return

    if re.compile("queue [0-9]+").match(content):
        await queue_gestion.get_queue(message, int(re.search("queue ([0-9]+)", content).group(1)))
        return

    if content == 'quit':
        await voice_gestion.disconnect(message)
        return

    if content == 'pause':
        await voice_gestion.pause_music(message)
        return

    if content == 'play' or content == 'p':
        if message.author.voice is None:
            await message.channel.send('You have to be connected to a voice channel in this server!')
            return

        await message.channel.send(f'{prefix}play <youtube url/playlist or search terms>')
        return

    if content.startswith('play ') or content.startswith('p '):
        if message.author.voice is None:
            await message.channel.send('You have to be connected to a voice channel in this server!')
            return

        if content.startswith('p '):
            content = content[2:].strip()
        else:
            content = content[5:].strip()
        await voice_gestion.play(message, content)
        return

    if content == 'playshuffle' or content == 'ps':
        if message.author.voice is None:
            await message.channel.send('You have to be connected to a voice channel in this server!')
            return

        await message.channel.send(f'{prefix}playshuffle <youtube url/playlist or search terms>')
        return

    if content.startswith('playshuffle ') or content.startswith('ps '):
        if message.author.voice is None:
            await message.channel.send('You have to be connected to a voice channel in this server!')
            return

        if content.startswith('ps '):
            content = content[3:].strip()
        else:
            content = content[12:].strip()
        await voice_gestion.play(message, content, shuffle=True)
        return

    if content == 'resume':
        await voice_gestion.resume_music(message)
        return

    if content == 'shuffle':
        await queue_gestion.shuffle_queue(message)
        return

    if content == 'skip' or content == 's':
        await voice_gestion.skip_music(message)
        return

    if content == 'stop':
        await voice_gestion.stop_music(message)
        return


@client_bot.event
async def on_reaction_add(reaction, user):
    if user == client_bot.user:
        return

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

        if reaction.emoji not in \
                globals_var.reactions_song[:len(globals_var.specifics_searches[user.guild.id]['searches']) + 1]:
            return

        await voice_gestion.select_specific_search(reaction.message,
                                                   globals_var.reactions_song.index(reaction.emoji) + 1)


def main():
    globals_var.initialize()
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
