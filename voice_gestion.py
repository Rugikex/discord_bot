import asyncio
import datetime

import discord
import youtube_dl

import globals_var
from globals_var import prefix, current_music
import queue_gestion
import youtube_requests

ydl_opts = {
    'format': 'bestaudio/best',
    'youtube_include_dash_manifest': False,
    'quiet': True
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 3',
    'options': '-vn -loglevel quiet',
}


async def next_music(message: discord.Message):
    guild_id = message.guild.id
    for voice_client in globals_var.client_bot.voice_clients:
        if voice_client.guild.id != guild_id:
            continue

        if globals_var.queues_musics[guild_id]:
            new_music = globals_var.queues_musics[guild_id].pop(0)

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(new_music.link, download=False)
                url = info['formats'][0]['url']

            audio = discord.FFmpegPCMAudio(url,
                                           before_options=FFMPEG_OPTIONS['before_options'],
                                           options=FFMPEG_OPTIONS['options'])

            voice_client.play(audio, after=lambda x=None: asyncio.run_coroutine_threadsafe(next_music(message),
                                                                                           globals_var.client_bot.loop))

            if guild_id in current_music:
                await current_music[guild_id]['message'].delete()

            current_music[guild_id] = {'start_time': datetime.datetime.now(),
                                       'time_spent': datetime.timedelta(seconds=0),
                                       'music': new_music,
                                       'is_paused': False,
                                       'message': None}
            current_music[guild_id]['message'] = await message.channel.send(f'Now playing {new_music}.')
        else:
            globals_var.queues_musics.pop(guild_id, None)
            await current_music[guild_id]['message'].delete()
            current_music.pop(guild_id, None)


async def get_voice_client(message: discord.Message):
    guilds_id = list(map(lambda n: n.channel.guild.id, globals_var.client_bot.voice_clients))
    if message.author.voice.channel.guild.id not in guilds_id:
        await message.channel.send('I\'m not connected to this server.')
        return None

    channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if message.author.voice.channel not in channels:
        await message.channel.send('We are in different voice channels.')
        return None

    for voice_client in globals_var.client_bot.voice_clients:
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

    current_music[message.guild.id]['is_paused'] = True
    current_music[message.guild.id]['time_spent'] += datetime.datetime.now() - \
                                                     current_music[message.guild.id]['start_time']


async def resume_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await message.channel.send('The music is already playing')
        return

    voice_client.resume()
    current_music[message.guild.id]['is_paused'] = False
    current_music[message.guild.id]['start_time'] = datetime.datetime.now()


async def skip_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    voice_client.stop()


async def stop_music(message: discord.Message):
    voice_client = await check_voice_client(message)
    if voice_client is None:
        return

    globals_var.queues_musics[voice_client.guild.id] = None
    voice_client.stop()


async def disconnect(message: discord.Message):
    voice_client = await get_voice_client(message)
    if voice_client is None:
        return

    globals_var.queues_musics.pop(voice_client.guild.id, None)
    voice_client.stop()
    await voice_client.disconnect()
    print(f"Bot disconnects to {voice_client.guild.name}.")


async def is_connected(message: discord.Message, channel):
    voice_channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
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


async def select_specific_search(message: discord.Message, number):
    if number < 1 or number > len(globals_var.specifics_searches[message.guild.id]['searches']):
        await message.channel.send(f'Choose between 1 and '
                                   f'{len(globals_var.specifics_searches[message.guild.id]["searches"])}')
        return

    music = [globals_var.specifics_searches[message.guild.id]['searches'][number - 1]]
    shuffle = globals_var.specifics_searches[message.guild.id]['shuffle']

    channel: discord.VoiceChannel = globals_var.client_bot.get_channel(message.author.voice.channel.id)
    if not await is_connected(message, channel):
        return

    for voice_client in globals_var.client_bot.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel != channel:
            continue

        await globals_var.specifics_searches[message.guild.id]['message'].delete()
        globals_var.specifics_searches.pop(message.guild.id, None)

        if voice_client.guild.id in globals_var.queues_musics:
            globals_var.queues_musics[voice_client.guild.id].extend(music)
            await message.channel.send(f"Added to queue: \"{music[0].title}\".")
        else:
            globals_var.queues_musics[voice_client.guild.id] = music

        if shuffle:
            await queue_gestion.shuffle_queue(message)

        if not voice_client.is_playing():
            await next_music(message)

        break


async def play(message: discord.Message, content: str, shuffle=False):
    channel: discord.VoiceChannel = globals_var.client_bot.get_channel(message.author.voice.channel.id)
    if not await is_connected(message, channel):
        return

    for voice_client in globals_var.client_bot.voice_clients:
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
            message_response = await message.channel.send(f"Searching for music related to {content}.")
            searches = youtube_requests.specific_search(content)
            if not searches:
                await message_response.edit(content=f"No music found for {content}")
                return

            globals_var.specifics_searches[message.guild.id] = {'searches': searches,
                                                                'shuffle': shuffle,
                                                                'user': message.author}
            msg_content = f'Select a track with reactions or' \
                          f'`{prefix}1-{len(globals_var.specifics_searches[message.guild.id]["searches"])}`:\n'
            for i in range(len(globals_var.specifics_searches[message.guild.id]['searches'])):
                msg_content += f'**{i + 1}:** {globals_var.specifics_searches[message.guild.id]["searches"][i]}\n'
            await message_response.edit(content=msg_content)
            globals_var.specifics_searches[message.guild.id]['message'] = message_response
            # Can't add multiples reactions at once
            for i in range(len(globals_var.specifics_searches[message.guild.id]['searches'])):
                try:
                    await message_response.add_reaction(globals_var.reactions_song[i])
                except discord.errors.NotFound:
                    pass
            return

        if not musics:
            await message.channel.send(f'No audio could be found for {content}')
            return

        if voice_client.guild.id in globals_var.queues_musics:
            globals_var.queues_musics[voice_client.guild.id].extend(musics)
            if len(musics) > 1:
                await message.channel.send(f"Added {len(musics)} musics to queue.")
            else:
                await message.channel.send(f"Added to queue: \"{musics[0].title}\".")
        else:
            globals_var.queues_musics[voice_client.guild.id] = musics
            if len(musics) - 1 > 1:
                await message.channel.send(f"Added {len(musics) - 1} musics to queue.")
            elif len(musics) == 2:
                await message.channel.send(f"Added to queue: \"{musics[1].title}\".")

        if shuffle:
            await queue_gestion.shuffle_queue(message)

        if not voice_client.is_playing():
            await next_music(message)
        break
