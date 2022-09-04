import asyncio
import datetime

import discord
import youtube_dl

import globals_var
import my_message
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


async def user_is_connected(interaction: discord.Interaction):
    if interaction.user.voice is None:
        await my_message.send(interaction, 'You have to be connected to a voice channel in this server!')
        return False

    return True


async def next_music(interaction: discord.Interaction):
    voice_client = await get_voice_client(interaction)

    if globals_var.queues_musics[interaction.guild_id] and voice_client is not None:
        new_music = globals_var.queues_musics[interaction.guild_id].pop(0)

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(new_music.link, download=False)
            url = info['formats'][0]['url']

        audio = discord.FFmpegPCMAudio(url,
                                       before_options=FFMPEG_OPTIONS['before_options'],
                                       options=FFMPEG_OPTIONS['options'])

        voice_client.play(audio, after=lambda x=None: asyncio.run_coroutine_threadsafe(next_music(interaction),
                                                                                       globals_var.client_bot.loop))

        if interaction.guild_id in current_music:
            await my_message.delete(current_music[interaction.guild_id]['message'])

        current_music[interaction.guild_id] = {'start_time': datetime.datetime.now(),
                                               'time_spent': datetime.timedelta(seconds=0),
                                               'music': new_music,
                                               'is_paused': False,
                                               'message': None}
        current_music[interaction.guild_id]['message'] = await my_message.send(interaction, f'Now playing {new_music}.')

    else:
        globals_var.queues_musics.pop(interaction.guild_id, None)
        await my_message.delete(current_music[interaction.guild_id]['message'])
        current_music.pop(interaction.guild_id, None)


async def get_voice_client(interaction: discord.Interaction):
    if not await user_is_connected(interaction):
        return None

    guilds_id = list(map(lambda n: n.channel.guild.id, globals_var.client_bot.voice_clients))
    if interaction.user.voice.channel.guild.id not in guilds_id:
        await my_message.send(interaction, 'I\'m not connected to this server.')
        return None

    channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if interaction.user.voice.channel not in channels:
        await my_message.send(interaction, 'We are in different voice channels.')
        return None

    for voice_client in globals_var.client_bot.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel != interaction.user.voice.channel:
            continue
        return voice_client

    return None


async def check_voice_client(interaction: discord.Interaction):
    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        return None

    if voice_client.source is None:
        await my_message.send(interaction, 'No music is playing.')
        return None

    return voice_client


async def pause_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if voice_client.is_paused():
        await my_message.send(interaction, 'The music is already paused.')
        return

    voice_client.pause()

    current_music[interaction.guild_id]['is_paused'] = True
    current_music[interaction.guild_id]['time_spent'] += datetime.datetime.now() - \
                                                         current_music[interaction.guild_id]['start_time']


async def resume_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await my_message.send(interaction, 'The music is already playing')
        return

    voice_client.resume()
    current_music[interaction.guild_id]['is_paused'] = False
    current_music[interaction.guild_id]['start_time'] = datetime.datetime.now()


async def skip_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    voice_client.stop()


async def stop_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    globals_var.queues_musics[interaction.guild_id] = None
    voice_client.stop()


async def disconnect(interaction: discord.Interaction):
    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        return

    globals_var.queues_musics.pop(interaction.guild_id, None)
    voice_client.stop()
    await voice_client.disconnect()
    print(f"Bot disconnects to {voice_client.guild.name}.")


async def is_connected(interaction: discord.Interaction, channel):
    voice_channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if channel in voice_channels:
        # Already connected
        return True
    try:
        await channel.connect(timeout=1.5)
    except asyncio.TimeoutError:
        await my_message.send(interaction, 'I can\'t connect to this channel!')
        return False
    except discord.errors.ClientException:
        await my_message.send(interaction, 'Already connected to {}.'
                              .format(list(set(voice_channels)
                                           .intersection(interaction.guild.voice_channels))[0].name))
        return False

    print(f"Bot connects to {interaction.guild.name}.")
    return True


async def select_specific_search(interaction: discord.Interaction, number):
    if number < 1 or number > len(globals_var.specifics_searches[interaction.guild_id]['searches']):
        await my_message.send(interaction, f'Choose between 1 and '
                                           f'{len(globals_var.specifics_searches[interaction.guild_id]["searches"])}')
        return

    music = [globals_var.specifics_searches[interaction.guild_id]['searches'][number - 1]]
    shuffle = globals_var.specifics_searches[interaction.guild_id]['shuffle']

    voice_client = await get_voice_client(interaction)

    await my_message.delete(globals_var.specifics_searches[interaction.guild_id]['message'])
    globals_var.specifics_searches.pop(interaction.guild_id, None)

    if voice_client.guild.id in globals_var.queues_musics:
        globals_var.queues_musics[voice_client.guild.id].extend(music)
        await my_message.send(interaction, f"Added to queue: \"{music[0].title}\".")
    else:
        globals_var.queues_musics[voice_client.guild.id] = music

    if shuffle:
        await queue_gestion.shuffle_queue(interaction)

    if not voice_client.is_playing():
        await next_music(interaction)


async def play(interaction: discord.Interaction, content: str, shuffle=False):
    if not await user_is_connected(interaction):
        return

    if not await is_connected(interaction, interaction.user.voice.channel):
        return

    voice_client = await get_voice_client(interaction)
    if voice_client is None:
        await my_message.send(interaction, "I have been disconnected.")
        return

    if content.startswith("https://www.youtube.com/playlist?list=") or \
            (content.startswith("https://www.youtube.com/watch?v=") and "list=" in content):
        message_loading = await my_message.send(interaction, "Loading playlist...")
        musics = youtube_requests.playlist_link(content)
        await my_message.delete(message_loading)
    elif content.startswith("https://www.youtube.com/watch?v="):
        musics = youtube_requests.single_link(content)
    else:
        await my_message.send(interaction, f"Searching for music related to {content}.")
        searches = youtube_requests.specific_search(content)
        if not searches:
            await my_message.edit_content(interaction, f"No music found for {content}")
            return

        globals_var.specifics_searches[interaction.guild_id] = {'searches': searches,
                                                                'shuffle': shuffle,
                                                                'user': interaction.user}
        msg_content = f'Select a track with reactions or' \
                      f'`{prefix}1-{len(globals_var.specifics_searches[interaction.guild.id]["searches"])}`:\n'
        for i in range(len(globals_var.specifics_searches[interaction.guild.id]['searches'])):
            msg_content += f'**{i + 1}:** {globals_var.specifics_searches[interaction.guild.id]["searches"][i]}\n'
        await my_message.edit_content(interaction, msg_content)
        globals_var.specifics_searches[interaction.guild.id]['message'] = await interaction.original_response()
        # Can't add multiples reactions at once
        for i in range(len(globals_var.specifics_searches[interaction.guild.id]['searches'])):
            await my_message.add_reaction(interaction, globals_var.reactions_song[i])
        return

    if not musics:
        await my_message.send(interaction, f'No audio could be found for {content}')
        return

    if voice_client.guild.id in globals_var.queues_musics:
        globals_var.queues_musics[voice_client.guild.id].extend(musics)
        if len(musics) > 1:
            await my_message.send(interaction, f"Added {len(musics)} musics to queue.")
        else:
            await my_message.send(interaction, f"Added to queue: \"{musics[0].title}\".")
    else:
        globals_var.queues_musics[voice_client.guild.id] = musics
        if len(musics) - 1 > 1:
            await my_message.send(interaction, f"Added {len(musics) - 1} musics to queue.")
        elif len(musics) == 2:
            await my_message.send(interaction, f"Added to queue: \"{musics[1].title}\".")

    if shuffle:
        await queue_gestion.shuffle_queue(interaction)

    if not voice_client.is_playing():
        await next_music(interaction)
