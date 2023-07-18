import functools

import discord

import globals_var
import my_functions
import voice_gestion


async def _check_is_playing(interaction: discord.Interaction):
    voice_client = await voice_gestion.get_voice_client(interaction)
    if voice_client is None:
        return False

    if interaction.guild_id not in globals_var.current_music:
        await my_functions.send(interaction, "No music is playing.")
        return False

    return True


async def get_lyrics_from_title(interaction: discord.Interaction):
    if not await _check_is_playing(interaction):
        return

    current_music = globals_var.current_music[interaction.guild_id]['music']

    genius_music = await globals_var.client_bot.loop\
        .run_in_executor(None, functools.partial(globals_var.genius.search_song, title=current_music.title))

    if not genius_music or not genius_music.lyrics:
        if current_music.search_by_user:
            await get_lyrics_from_search(interaction)
        else:
            await my_functions.send(interaction, f'No lyrics found with "{current_music.title}".')
        return

    await my_functions.send(interaction, genius_music.lyrics)


async def get_lyrics_from_search(interaction: discord.Interaction):
    if not await _check_is_playing(interaction):
        return

    current_music = globals_var.current_music[interaction.guild_id]['music']

    genius_music = await globals_var.client_bot.loop\
        .run_in_executor(None,functools.partial(globals_var.genius.search_song, title=current_music.search_by_user))

    if not genius_music or not genius_music.lyrics:
        await my_functions.send(interaction, f'No lyrics found with "{current_music.search_by_user}".')
        return

    await my_functions.send(interaction, genius_music.lyrics)
