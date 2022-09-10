import asyncio
import datetime
import random
import re

import discord
import yt_dlp

import globals_var
import my_functions
from globals_var import current_music
import queue_gestion
import youtube_requests

ydl_opts = {
    'audio-quality': 0,
    'extract-audio': True,
    'format': 'bestaudio',
    'fps': None,
    'youtube_include_dash_manifest': False,
    'quiet': True
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 3',
    'options': '-vn -loglevel quiet',
}


async def user_is_connected(interaction: discord.Interaction):
    if interaction.user.voice is None:
        await my_functions.send(interaction, 'You have to be connected to a voice channel in this server!')
        return False

    return True


async def next_music(interaction: discord.Interaction, channel, guild_id):
    voice_client = await get_voice_client(interaction, channel, check=False)

    if globals_var.queues_musics[guild_id] and voice_client is not None:
        new_music = globals_var.queues_musics[guild_id].pop(0)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(new_music.link, download=False)

        url = None
        for info_format in info['formats']:
            if 'asr' not in info_format:
                continue
            url = info_format['url']
            break

        if url is None:
            await my_functions.send_by_channel(interaction.channel, f'Can\'t find stream for listening "{new_music}".\n'
                                                                    f'The music is skipped.')
            await next_music(interaction, channel, guild_id)
            return

        audio = discord.FFmpegPCMAudio(url,
                                       before_options=FFMPEG_OPTIONS['before_options'],
                                       options=FFMPEG_OPTIONS['options'])

        voice_client.play(audio, after=lambda x=None: asyncio.run_coroutine_threadsafe(
            next_music(interaction, channel, guild_id),
            globals_var.client_bot.loop
        ))

        if interaction.guild_id in current_music:
            await my_functions.delete_msg(current_music[guild_id]['message'])

        current_music[guild_id] = {'start_time': datetime.datetime.now(),
                                   'time_spent': datetime.timedelta(seconds=0),
                                   'music': new_music,
                                   'is_paused': False,
                                   'message': None}
        message = await my_functions.send_by_channel(interaction.channel, f'Now playing {new_music}.')
        current_music[guild_id]['message'] = message
    else:
        if guild_id in globals_var.queues_musics:
            globals_var.queues_musics.pop(guild_id, None)
        if guild_id in current_music:
            await my_functions.delete_msg(current_music[guild_id]['message'])
            current_music.pop(guild_id, None)
        if guild_id in globals_var.queues_message:
            await my_functions.delete_msg(globals_var.queues_message[guild_id])
            globals_var.queues_message.pop(guild_id, None)


async def get_voice_client(interaction: discord.Interaction, channel, check=True):
    if check and not await user_is_connected(interaction):
        return None

    guilds_id = list(map(lambda n: n.channel.guild.id, globals_var.client_bot.voice_clients))
    if interaction.guild_id not in guilds_id:
        await my_functions.send(interaction, 'I\'m not connected to this server.')
        return None

    channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if check and channel not in channels:
        await my_functions.send(interaction, 'We are in different voice channels.')
        return None

    for voice_client in globals_var.client_bot.voice_clients:
        voice_client: discord.VoiceClient
        if voice_client.channel.guild != channel.guild:
            continue
        return voice_client

    return None


async def check_voice_client(interaction: discord.Interaction):
    voice_client = await get_voice_client(interaction, interaction.user.voice.channel)
    if voice_client is None:
        return None

    if voice_client.source is None:
        await my_functions.send(interaction, 'No music is playing.')
        return None

    return voice_client


async def pause_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if voice_client.is_paused():
        await my_functions.send(interaction, 'The music is already paused.')
        return

    voice_client.pause()

    current_music[interaction.guild_id]['is_paused'] = True
    current_music[interaction.guild_id]['time_spent'] += datetime.datetime.now() - \
                                                         current_music[interaction.guild_id]['start_time']

    await my_functions.send(interaction, 'The music is paused.')


async def resume_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    if not voice_client.is_paused():
        await my_functions.send(interaction, 'The music is already playing.')
        return

    voice_client.resume()
    current_music[interaction.guild_id]['is_paused'] = False
    current_music[interaction.guild_id]['start_time'] = datetime.datetime.now()

    await my_functions.send(interaction, 'The music resumes.')


async def skip_music(interaction: discord.Interaction, number):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    for i in range(1, number):
        if globals_var.queues_musics[interaction.guild_id]:
            globals_var.queues_musics[interaction.guild_id].pop(0)
        else:
            break

    voice_client.stop()

    await my_functions.send(interaction, f'Skip {current_music[interaction.guild_id]["music"]}.')


async def stop_music(interaction: discord.Interaction):
    voice_client = await check_voice_client(interaction)
    if voice_client is None:
        return

    globals_var.queues_musics[interaction.guild_id] = None
    voice_client.stop()

    await my_functions.send(interaction, 'The bot stops playing musics.')


async def disconnect(interaction: discord.Interaction):
    voice_client = await get_voice_client(interaction, interaction.user.voice.channel)
    if voice_client is None:
        return

    globals_var.queues_musics.pop(interaction.guild_id, None)
    voice_client.stop()

    await my_functions.send(interaction, 'The bot is disconnected.')
    print(f"Bot disconnects to {voice_client.guild.name}.")

    await voice_client.disconnect()


async def is_connected(interaction: discord.Interaction, channel):
    voice_channels = list(map(lambda n: n.channel, globals_var.client_bot.voice_clients))
    if channel in voice_channels:
        # Already connected
        return True
    try:
        await channel.connect(timeout=1.5)
    except asyncio.TimeoutError:
        await my_functions.send(interaction, 'I can\'t connect to this channel!')
        return False
    except discord.errors.ClientException:
        await my_functions.send(interaction, 'Already connected to {}.'
                                .format(list(set(voice_channels)
                                             .intersection(interaction.guild.voice_channels))[0].name))
        return False

    globals_var.queues_musics[interaction.guild_id] = [globals_var.wololo]
    await next_music(interaction, channel, interaction.guild_id)

    print(f"Bot connects to {interaction.guild.name}.")
    return True


async def select_specific_search(interaction: discord.Interaction, number, content):
    music = [globals_var.specifics_searches[interaction.guild_id]['searches'][number]]
    shuffle = globals_var.specifics_searches[interaction.guild_id]['shuffle']
    if 'position' in globals_var.specifics_searches[interaction.guild_id]:
        position = globals_var.specifics_searches[interaction.guild_id]['position']
    else:
        position = None

    voice_client = await get_voice_client(interaction, interaction.user.voice.channel)
    if voice_client is None:
        return

    await my_functions.delete_msg(globals_var.specifics_searches[interaction.guild_id]['message'])
    globals_var.specifics_searches.pop(interaction.guild_id, None)

    await queue_gestion.add_in_queue(interaction, music, position, content)

    if shuffle and not position:
        await queue_gestion.shuffle_queue(interaction)

    if not voice_client.is_playing():
        await next_music(interaction, interaction.user.voice.channel, interaction.guild_id)


async def create_button_select(number, content):
    button = discord.ui.Button(emoji=globals_var.reactions_song[number])

    async def button_callback(interact: discord.Interaction):
        await select_specific_search(interact, number, content)

    button.callback = button_callback
    return button


async def play(interaction: discord.Interaction, content: str, shuffle=False, position=None):
    if not await user_is_connected(interaction):
        return

    if not await is_connected(interaction, interaction.user.voice.channel):
        return

    voice_client = await get_voice_client(interaction, interaction.user.voice.channel)
    if voice_client is None:
        await my_functions.send(interaction, "I have been disconnected.")
        return

    if (position and interaction.guild_id not in globals_var.queues_musics) or \
            (position and interaction.guild_id in globals_var.queues_musics and
             (position < 1 or position > len(globals_var.queues_musics[interaction.guild_id]))):
        position = None

    if re.match("^((https://)?(www\.|music\.)?youtube\.com/playlist\?list=.+)", content) or \
            re.match("^((https://)?www\.youtube\.com/watch\?v=.+&list=[^&]+)", content):
        await my_functions.send(interaction, "Loading playlist...")
        musics = await youtube_requests.playlist_link(interaction, content)
    elif re.match("^((https://)?www\.youtube\.com/watch\?v=.+)", content):
        await my_functions.send(interaction, "Loading music...")
        musics = await globals_var.client_bot.loop.run_in_executor(None, youtube_requests.single_link, content)
    else:
        if interaction.guild_id in globals_var.specifics_searches:
            await my_functions.delete_msg(globals_var.specifics_searches[interaction.guild_id]['message'])

        await my_functions.send(interaction, f"Searching for music related to {content}.")
        searches = await globals_var.client_bot.loop.run_in_executor(None, youtube_requests.specific_search, content)
        if not searches:
            await my_functions.edit(interaction, content=f"No music found for \"{content}\".")
            return

        globals_var.specifics_searches[interaction.guild_id] = {'searches': searches,
                                                                'shuffle': shuffle,
                                                                'position': position,
                                                                'user': interaction.user,
                                                                'message': await interaction.original_response()}
        msg_content = f'Select a track with buttons.\n\n'
        for i in range(len(globals_var.specifics_searches[interaction.guild_id]['searches'])):
            msg_content += f'**{i + 1}:** {globals_var.specifics_searches[interaction.guild_id]["searches"][i]}\n'

        view = discord.ui.View()
        for i in range(len(globals_var.specifics_searches[interaction.guild_id]['searches'])):
            view.add_item(await create_button_select(i, content))

        await my_functions.edit(interaction, content=msg_content, view=view)

        return

    if not musics and \
            re.match(
                "^(https://)?www\.youtube\.com/watch\?v=[^&\n]+((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)("
                "&list=[^&\n]+)?)",
                content):
        match = re.match(
            "^(https://)?(www\.youtube\.com/watch\?v=[^&\n]+)((&list=[^&\n]+)(&index=[^&\n]+)?|(&index=[^&\n]+)(&list=["
            "^&\n]+)?)",
            content)

        await my_functions.edit(interaction, "No playlist found, loading music...")
        musics = await globals_var.client_bot.loop.run_in_executor(None, youtube_requests.single_link,
                                                                   match[match.lastindex - 1])

    if not musics:
        await my_functions.edit(interaction, f'No audio found for "{content}".')
        return

    await my_functions.delete_msg(await interaction.original_response())

    if shuffle and position:
        random.shuffle(musics)

    await queue_gestion.add_in_queue(interaction, musics, position, content)

    if shuffle and not position:
        await queue_gestion.shuffle_queue(interaction)

    voice_client = discord.utils.get(globals_var.client_bot.voice_clients, guild=interaction.guild)
    if voice_client.source is None or interaction.guild_id not in globals_var.current_music:
        await next_music(interaction, voice_client.channel, interaction.guild_id)
