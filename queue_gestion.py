import datetime
import math
import random

import discord

import globals_var
import my_functions
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


async def remove_musics(interaction: discord.Interaction, begin, end):
    voice_client = await voice_gestion.check_voice_client(interaction)
    if voice_client is None:
        return

    counter = 0
    for i in range(begin, end + 1):
        if globals_var.queues_musics[interaction.guild_id]:
            pop = globals_var.queues_musics[interaction.guild_id].pop(begin - 1)
            print("music pop:", pop)
            counter += 1
        else:
            break

    await my_functions.send(interaction, f"Remove {counter} music(s).")


async def get_queue(interaction: discord.Interaction, page):
    voice_client = await voice_gestion.check_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        await my_functions.send(interaction, "Queue is empty!")
        return

    if page <= 0:
        await my_functions.send(interaction, "Number page is incorrect!")
        return

    if page != 1 and not globals_var.queues_musics[interaction.guild_id][(page - 1) * 10:page * 10]:
        await my_functions.send(interaction, "Number page is too big!")
        return

    content = message_queue(interaction, page)

    if interaction.guild_id in globals_var.queues_message:
        await my_functions.delete_msg(await globals_var.queues_message[interaction.guild_id])

    await my_functions.send(interaction, content)
    await buttons_on_message_queue(interaction, page)
    globals_var.queues_message[interaction.guild_id] = interaction.original_response()


async def shuffle_queue(interaction: discord.Interaction):
    voice_client = await voice_gestion.get_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        return

    random.shuffle(globals_var.queues_musics[interaction.guild_id])


async def clear_queue(interaction: discord.Interaction):
    voice_client = await voice_gestion.check_voice_client(interaction)
    if voice_client is None:
        return

    if interaction.guild_id not in globals_var.queues_musics:
        return

    globals_var.queues_musics[interaction.guild_id] = None


def message_queue(interaction: discord.Interaction, page):
    max_page = max(math.ceil(len(globals_var.queues_musics[interaction.guild_id]) / 10), 1)
    msg_content = f'Queue list (page {page}/{max_page}):\n'
    if page == 1:
        msg_content += f'**Now.** {globals_var.current_music[interaction.guild_id]["music"].title} ['
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


async def buttons_on_message_queue(interaction: discord.Interaction, page):
    view = discord.ui.View()
    if page != 1:
        button = discord.ui.Button(emoji=globals_var.reactions_queue[0])

        async def button_callback(interact: discord.Interaction):
            await get_queue(interact, page - 1)

        button.callback = button_callback
        view.add_item(button)

    if globals_var.queues_musics[interaction.guild_id][page * 10:]:
        button = discord.ui.Button(emoji=globals_var.reactions_queue[1])

        async def button_callback(interact: discord.Interaction):
            await get_queue(interact, page + 1)

        button.callback = button_callback
        view.add_item(button)

    await my_functions.edit(interaction, view=view)
