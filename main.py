import asyncio
import datetime
import os
import random

import discord
from dotenv import load_dotenv
import youtube_dl

import youtube_requests

load_dotenv()
discord_key = os.getenv("DISCORD_KEY")
client = discord.Client()
prefix = 'tk'
reactions_song = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
current_music = {}
"""
Store by guild id
Contains a list of MusicItem(s) if users request multiples musics
"""
queues_musics = {}
"""
Store by guild id
Contains searches if user requests song with search terms
Each key stores a dict containing:
    'searches': list of 1 to 5 MusicItem about the last search terms
    'shuffle': boolean to know if the music must be shuffled
    'user': user who requested the song
    'message': message that shows searches
"""
specifics_searches = {}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 3',
    'options': '-vn',
}


async def next_music(message: discord.Message):
    guild_id = message.guild.id
    for voice_client in client.voice_clients:
        if voice_client.guild.id != guild_id:
            continue

        if queues_musics[guild_id]:
            new_music = queues_musics[guild_id].pop(0)

            ydl_opts = {'format': 'bestaudio'}
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(new_music.link, download=False)
                url = info['formats'][0]['url']

            audio = discord.FFmpegPCMAudio(url,
                                           before_options=FFMPEG_OPTIONS['before_options'],
                                           options=FFMPEG_OPTIONS['options'])
            current_music[guild_id] = audio

            voice_client.play(audio, after=lambda x=None: asyncio.run_coroutine_threadsafe(next_music(message),
                                                                                           client.loop))
            await message.channel.send(f'Now playing {new_music}.')
        else:
            queues_musics.pop(guild_id, None)


async def get_queue_total_time(message: discord.Message):
    res = datetime.timedelta(0)
    for item in queues_musics[message.guild.id]:
        res += item.duration
    await message.channel.send(res)


async def get_voice_client(message: discord.Message):
    guilds_id = list(map(lambda n: n.channel.guild.id, client.voice_clients))
    if message.author.voice.channel.guild.id not in guilds_id:
        await message.channel.send('I\'m not connected to this server.')
        return None

    channels = list(map(lambda n: n.channel, client.voice_clients))
    if message.author.voice.channel not in channels:
        await message.channel.send('We are in different voice channels.')
        return None

    for voice_client in client.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel != message.author.voice.channel:
            continue
        return voice_client


async def check_voice_client(message: discord.Message):
    voice_client = await get_voice_client(message)
    if voice_client is None:
        return None

    if voice_client.source is None:
        await message.channel.send('No music is playing.')
        return None

    return voice_client


async def pause_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    if voice_client.is_paused():
        await message.channel.send('The music is already paused.')
        return

    voice_client.pause()


async def resume_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await message.channel.send('The music is already playing')
        return

    voice_client.resume()


async def skip_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    voice_client.stop()


async def stop_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    queues_musics[voice_client.guild.id] = None
    voice_client.stop()


async def disconnect(message: discord.Message):
    voice_client = await get_voice_client(message)
    if voice_client is None:
        return

    queues_musics.pop(voice_client.guild.id, None)
    voice_client.stop()
    await voice_client.disconnect()
    print(f"Bot disconnects to {voice_client.guild.name}.")


async def is_connected(message: discord.Message, channel):
    voice_channels = list(map(lambda n: n.channel, client.voice_clients))
    if channel in voice_channels:
        # Already connected
        return True
    try:
        await channel.connect(timeout=1.5)
    except asyncio.TimeoutError:
        await message.channel.send('I can\'t connect to this channel!')
        return False
    except discord.errors.ClientException:
        await message.channel.send('Already connected to {}.'
                                   .format(list(set(voice_channels)
                                                .intersection(message.guild.voice_channels))[0].name))
        return False

    print(f"Bot connects to {message.guild.name}.")
    return True


async def play(message: discord.Message, content: str, shuffle=False):
    channel: discord.VoiceChannel = client.get_channel(message.author.voice.channel.id)
    if not await is_connected(message, channel):
        return

    for voice_client in client.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel != channel:
            continue

        if content.startswith("https://www.youtube.com/playlist?list=") or \
                (content.startswith("https://www.youtube.com/watch?v=") and "list=" in content):
            message_loading = await message.channel.send("Loading playlist...")
            musics = youtube_requests.playlist_link(content)
            await message_loading.delete()
        elif content.startswith("https://www.youtube.com/watch?v="):
            musics = youtube_requests.single_link(content)
        else:
            message_loading = await message.channel.send(f"Searching for music related to {content}.")
            searches = youtube_requests.specific_search(content)
            await message_loading.delete()
            if not searches:
                await message.channel.send(f"No music found for {content}")
                return

            specifics_searches[message.guild.id] = {'searches': searches,
                                                    'shuffle': shuffle,
                                                    'user': message.author}
            msg_content = f'Select a track with reactions or `{prefix}' \
                          f'1-{len(specifics_searches[message.guild.id]["searches"])}`:\n'
            for i in range(len(specifics_searches[message.guild.id]['searches'])):
                msg_content += f'**{i + 1}:** {specifics_searches[message.guild.id]["searches"][i]}\n'
            message = await message.channel.send(msg_content)
            specifics_searches[message.guild.id]['message'] = message
            # Can't add multiples reactions at once
            for i in range(len(specifics_searches[message.guild.id]['searches'])):
                await message.add_reaction(reactions_song[i])
            print(specifics_searches[message.guild.id])
            return

        if not musics:
            await message.channel.send(f'No audio could be found for {content}')
            return

        if voice_client.guild.id in queues_musics:
            queues_musics[voice_client.guild.id].extend(musics)
            if len(musics) > 1:
                await message.channel.send(f"Added {len(musics)} musics to queue.")
            else:
                await message.channel.send(f"Added to queue: \"{musics[0].title}\".")
        else:
            queues_musics[voice_client.guild.id] = musics
            if len(musics) - 1 > 1:
                await message.channel.send(f"Added {len(musics) - 1} musics to queue.")
            elif len(musics) == 2:
                await message.channel.send(f"Added to queue: \"{musics[1].title}\".")

        if shuffle:
            await shuffle_queue(message)

        if not voice_client.is_playing():
            await next_music(message)
        break


async def select_specific_search(message: discord.Message, number):
    if number < 1 or number > len(specifics_searches[message.guild.id]['searches']):
        await message.channel.send(f'Choose between 1 and {len(specifics_searches[message.guild.id]["searches"])}')
        return

    music = [specifics_searches[message.guild.id]['searches'][number - 1]]
    shuffle = specifics_searches[message.guild.id]['shuffle']

    channel: discord.VoiceChannel = client.get_channel(message.author.voice.channel.id)
    if not await is_connected(message, channel):
        return

    for voice_client in client.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel != channel:
            continue

        await specifics_searches[message.guild.id]['message'].delete()
        specifics_searches.pop(message.guild.id, None)

        if voice_client.guild.id in queues_musics:
            queues_musics[voice_client.guild.id].extend(music)
            await message.channel.send(f"Added to queue: \"{music[0].title}\".")
        else:
            queues_musics[voice_client.guild.id] = music

        if shuffle:
            await shuffle_queue(message)

        if not voice_client.is_playing():
            await next_music(message)

        break


async def shuffle_queue(message: discord.Message):
    voice_client = await get_voice_client(message)
    if voice_client is None:
        return

    if message.guild.id not in queues_musics:
        return

    random.shuffle(queues_musics[message.guild.id])
    await message.add_reaction("🔀")


async def msg_help(message: discord.Message):
    content = f"`{prefix}help` or `{prefix}h`: Display this message.\n" \
              f"`{prefix}play` or `{prefix}p`: Play music with <youtube url/playlist or search terms>.\n" \
              f"`{prefix}playshuffle` or `{prefix}ps`: Play music and shuffle queue.\n" \
              f"`{prefix}shuffle`: Shuffle queue.\n" \
              f"`{prefix}skip` or `{prefix}s`: Skip current music.\n" \
              f"`{prefix}stop`: Stop current music.\n" \
              f"`{prefix}resume`: Resume current music.\n" \
              f"`{prefix}quit`: Disconnect the bot.\n"

    await message.channel.send(content)


async def test(message: discord.Message):
    print(current_music[message.guild.id].read())


@client.event
async def on_ready():
    guilds = []
    for guild in client.guilds:
        guilds.append(guild.name)
    print(f'Logged in as {client.user} to {guilds}.')


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if not message.content.startswith(prefix):
        return

    content = str(message.content[len(prefix):])
    if len(content) == 0:
        await message.channel.send(f'Need help? Check {prefix}help.')
        return

    if message.guild.id in specifics_searches:
        if message.author != specifics_searches[message.guild.id]['user']:
            return

        number = 1
        try:
            number = int(content)
        except ValueError:
            specifics_searches.pop(message.guild.id, None)

        if message.guild.id in specifics_searches:
            await select_specific_search(message, number)
            return

    if content == 'help' or content == 'h':
        await msg_help(message)
        return

    if content == 'test':
        channel = message.channel
        await channel.send('Say hello!')

    if content == 'quit':
        await disconnect(message)
        return

    if content == 'pause':
        await pause_music(message)
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
        await play(message, content)
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
        await play(message, content, shuffle=True)
        return

    if content == 'resume':
        await resume_music(message)
        return

    if content == 'shuffle':
        await shuffle_queue(message)
        return

    if content == 'skip' or content == 's':
        await skip_music(message)
        return

    if content == 'stop':
        await stop_music(message)
        return


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return

    if user.guild.id not in specifics_searches:
        return

    if reaction.message != specifics_searches[user.guild.id]['message']:
        return

    if user != specifics_searches[user.guild.id]['user']:
        print(user)
        print(specifics_searches[user.guild.id]['user'])
        return

    if reaction.emoji not in reactions_song[:len(specifics_searches[user.guild.id]['searches']) + 1]:
        return

    await select_specific_search(reaction.message, reactions_song.index(reaction.emoji) + 1)


def main():
    client.run(discord_key)


if __name__ == "__main__":
    main()
