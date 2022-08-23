import re
import discord

import globals_var
import queue_gestion
import voice_gestion


prefix = 'tk'


async def msg_help(message: discord.Message):
    content = f"`{prefix}help` or `{prefix}h`: Display this message.\n" \
              f"`{prefix}play` or `{prefix}p`: Play music with <youtube url/playlist or search terms>.\n" \
              f"`{prefix}playshuffle` or `{prefix}ps`: Play music and shuffle queue.\n" \
              f"`{prefix}shuffle`: Shuffle queue.\n" \
              f"`{prefix}skip` or `{prefix}s`: Skip current music.\n" \
              f"`{prefix}clear`: Clear queue.\n" \
              f"`{prefix}stop`: Stop current music.\n" \
              f"`{prefix}resume`: Resume current music.\n" \
              f"`{prefix}quit`: Disconnect the bot.\n"

    await message.channel.send(content)


@globals_var.client_bot.event
async def on_ready():
    guilds = []
    for guild in globals_var.client_bot.guilds:
        guilds.append(guild.name)
    print(f'Logged in as {globals_var.client_bot.user} to {guilds}.')


@globals_var.client_bot.event
async def on_message(message: discord.Message):
    if message.author == globals_var.client_bot.user:
        return

    if not message.content.startswith(prefix):
        return

    content = str(message.content[len(prefix):])
    if len(content) == 0:
        await message.channel.send(f'Need help? Check {prefix}help.')
        return

    if message.guild.id in globals_var.specifics_searches and \
            message.author == globals_var.specifics_searches[message.guild.id]['user']:
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


@globals_var.client_bot.event
async def on_reaction_add(reaction, user):
    if user == globals_var.client_bot.user:
        return

    if user.guild.id in globals_var.queues_musics and reaction.message.author == globals_var.client_bot.user \
            and reaction.message.content.startswith("Queue list(page "):
        if reaction.emoji not in globals_var.reactions_queue:
            return

        page = int(re.search("Queue list\(page (.*)\):", reaction.message.content).group(1))
        if page == 1 and reaction.emoji == globals_var.reactions_queue[0]:
            return

        if not globals_var.queues_musics[reaction.message.guild.id][page * 10:] \
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

        await voice_gestion.select_specific_search(reaction.message, globals_var.reactions_song.index(reaction.emoji)+1)


def main():
    globals_var.initialize()
    globals_var.client_bot.run(globals_var.discord_key)


if __name__ == "__main__":
    main()
