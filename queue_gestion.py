import datetime
import math
import random

import discord

import globals_var
import my_message
import voice_gestion


def get_queue_total_time(guild_id):
    res = datetime.timedelta(0)
    for item in globals_var.queues_musics[guild_id]:
        res += item.duration

    res += globals_var.current_music[guild_id]['music'].duration
    if globals_var.current_music[guild_id]['is_paused']:
        res -= globals_var.current_music[guild_id]['time_spent']
    else:
        duration = datetime.datetime.now() + globals_var.current_music[guild_id]['time_spent'] \
                   - globals_var.current_music[guild_id]['start_time']
        res -= duration
    return res - datetime.timedelta(microseconds=res.microseconds)


async def get_queue(interaction: discord.Interaction, page):
    voice_client = await voice_gestion.check_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        await my_message.send(interaction, "Queue is empty!")
        return

    if page != 1 and not globals_var.queues_musics[interaction.guild_id][(page - 1) * 10:page * 10]:
        await my_message.send(interaction, "Number page is too big!")
        return

    message_response = await my_message.send(interaction, message_queue(interaction, page))
    await reactions_on_message_queue(message_response, page)


async def shuffle_queue(interaction: discord.Interaction):
    voice_client = await voice_gestion.get_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        return

    random.shuffle(globals_var.queues_musics[interaction.guild_id])
    await my_message.add_reaction(interaction, "🔀")


async def clear_queue(interaction: discord.Interaction):
    voice_client = await voice_gestion.check_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        return

    globals_var.queues_musics[interaction.guild_id] = None
    await my_message.add_reaction(interaction, "💣")


def message_queue(interaction: discord.Interaction, page):
    msg_content = f'Queue list (page {page}/{max(math.ceil(len(globals_var.queues_musics[interaction.guild_id])), 1)}):\n'
    if page == 1:
        msg_content += f'**Now.** {globals_var.current_music[interaction.guild_id]["music"].title } ['
        if globals_var.current_music[interaction.guild_id]['is_paused']:
            msg_content += f"{str(globals_var.current_music[interaction.guild_id]['time_spent']).split('.')[0]}"
        else:
            duration = datetime.datetime.now() + globals_var.current_music[interaction.guild_id]['time_spent'] \
                       - globals_var.current_music[interaction.guild_id]['start_time']
            duration_without_ms = str(duration).split('.')[0]
            msg_content += f"{duration_without_ms}"

        msg_content += f" / {globals_var.current_music[interaction.guild_id]['music'].duration}]\n"

    for i in range(len(globals_var.queues_musics[interaction.guild_id][(page - 1) * 10:page * 10])):
        msg_content += f'**{i + 1 + (page - 1) * 10}.** {globals_var.queues_musics[interaction.guild_id][i]}\n'
    msg_content += f'__Total musics:__ {len(globals_var.queues_musics[interaction.guild_id]) + 1}\n' \
                   f'__Total time:__ {get_queue_total_time(interaction.guild_id)}'
    return msg_content


async def reactions_on_message_queue(interaction: discord.Interaction, page):
    if page != 1:
        await my_message.add_reaction(interaction, globals_var.reactions_queue[0])

    if globals_var.queues_musics[interaction.guild_id][page * 10:]:
        await my_message.add_reaction(interaction, globals_var.reactions_queue[1])
