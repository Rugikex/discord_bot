import datetime
import random

import discord

import globals_var
import my_message
import voice_gestion


def get_queue_total_time(message: discord.Message):
    res = datetime.timedelta(0)
    for item in globals_var.queues_musics[message.guild.id]:
        res += item.duration
    return res


async def get_queue(message: discord.Message, page):
    voice_client = await voice_gestion.check_voice_client(message)
    if voice_client is None:
        return

    if message.guild.id not in globals_var.queues_musics or not globals_var.queues_musics[message.guild.id]:
        await message.channel.send("Queue is empty!")
        return

    if not globals_var.queues_musics[message.guild.id][(page - 1) * 10:page * 10]:
        await message.channel.send("Number page is too big!")
        return

    message_response = await message.channel.send(message_queue(message, page))
    await reactions_on_message_queue(message_response, page)


async def shuffle_queue(message: discord.Message):
    voice_client = await voice_gestion.get_voice_client(message)
    if voice_client is None:
        return

    if message.guild.id not in globals_var.queues_musics:
        return

    random.shuffle(globals_var.queues_musics[message.guild.id])
    await my_message.add_reaction(message, "🔀")


async def clear_queue(message: discord.Message):
    voice_client = await voice_gestion.check_voice_client(message)
    if voice_client is None:
        return

    if message.guild.id not in globals_var.queues_musics:
        return

    globals_var.queues_musics[voice_client.guild.id] = None
    await my_message.add_reaction(message, "💣")


def message_queue(message: discord.Message, page):
    msg_content = f'Queue list(page {page}):\n'
    for i in range(len(globals_var.queues_musics[message.guild.id][(page - 1) * 10:page * 10])):
        msg_content += f'**{i + 1 + (page - 1) * 10}.** {globals_var.queues_musics[message.guild.id][i]}\n'
    msg_content += f'__Total time:__ {get_queue_total_time(message)}'
    return msg_content


async def reactions_on_message_queue(message: discord.Message, page):
    if page != 1:
        await my_message.add_reaction(message, globals_var.reactions_queue[0])

    if globals_var.queues_musics[message.guild.id][page * 10:]:
        await my_message.add_reaction(message, globals_var.reactions_queue[1])
