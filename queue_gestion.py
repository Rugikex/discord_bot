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


async def move_music(interaction: discord.Interaction, position, new_position):
    if interaction.guild_id not in globals_var.queues_musics or not globals_var.queues_musics[interaction.guild_id]:
        await my_functions.send(interaction, "Queue is empty!")
        return

    if new_position < 1 or position < 1 \
            or len(globals_var.queues_musics[interaction.guild_id]) + 1 < position \
            or len(globals_var.queues_musics[interaction.guild_id]) + 1 < new_position:
        await my_functions.send(interaction, "Numbers are incorrect!")
        return

    music = globals_var.queues_musics[interaction.guild_id].pop(position - 1)
    globals_var.queues_musics[interaction.guild_id].insert(new_position - 1, music)

    await my_functions.send(interaction, f"Move {music} from position {position} to position {new_position}.")


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


async def get_queue(interaction: discord.Interaction, page, is_new=True):
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

    if interaction.guild_id in globals_var.queues_message and is_new:
        await my_functions.delete_msg(globals_var.queues_message[interaction.guild_id])

    if interaction.guild_id in globals_var.queues_message and not is_new:
        await my_functions.edit_response(globals_var.queues_message[interaction.guild_id], content=content)
        await edit_buttons_on_message_queue(globals_var.queues_message[interaction.guild_id], interaction.guild_id, page)
        await interaction.response.defer()
    else:
        await my_functions.send(interaction, content)
        await create_buttons_on_message_queue(interaction, page)
        globals_var.queues_message[interaction.guild_id] = await interaction.original_response()


async def add_in_queue(interaction: discord.Interaction, musics, position, content):
    if position is not None:
        for i in range(len(musics)):
            globals_var.queues_musics[interaction.guild_id].insert(position - 1 + i, musics[i])
        if len(musics) > 1:
            await my_functions.send(interaction, f"Added {len(musics)} musics to {position} at "
                                                 f"{position + len(musics)} in queue.\n"
                                                 f"From: \"{content}\".")
        else:
            await my_functions.send(interaction, f"Added in position {position} to queue: \"{musics[0]}\".\n"
                                                 f"From: \"{content}\".")

    elif interaction.guild_id in globals_var.queues_musics:
        globals_var.queues_musics[interaction.guild_id].extend(musics)
        if len(musics) > 1:
            await my_functions.send(interaction, f"Added {len(musics)} musics to queue.\n"
                                                 f"From: \"{content}\".")
        else:
            await my_functions.send(interaction, f"Added to queue: \"{musics[0]}\".\n"
                                                 f"From: \"{content}\".")
    else:
        globals_var.queues_musics[interaction.guild_id] = musics
        if len(musics) - 1 > 1:
            await my_functions.send(interaction, f"Added {len(musics)} musics to queue.\n"
                                                 f"From: \"{content}\".")
        elif len(musics) == 2:
            await my_functions.send(interaction, f"Added to queue: \"{musics[1]}\".\n"
                                                 f"From: \"{content}\".")


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
        number = i + (page - 1) * 10
        msg_content += f'**{number + 1}.** {globals_var.queues_musics[interaction.guild_id][number]}\n'
    msg_content += f'__Total musics:__ {len(globals_var.queues_musics[interaction.guild_id]) + 1}\n' \
                   f'__Total time:__ {get_queue_total_time(interaction.guild_id)}'
    return msg_content


def create_view_queue(guild_id, page):
    view = discord.ui.View()
    button = discord.ui.Button(emoji=globals_var.reactions_queue[0])

    async def button_callback(interact: discord.Interaction):
        await get_queue(interact, page - 1, is_new=False)

    button.callback = button_callback
    if page == 1:
        button.disabled = True
    view.add_item(button)

    button = discord.ui.Button(emoji=globals_var.reactions_queue[1])

    async def button_callback(interact: discord.Interaction):
        await get_queue(interact, page + 1, is_new=False)

    button.callback = button_callback
    if not globals_var.queues_musics[guild_id][page * 10:]:
        button.disabled = True
    view.add_item(button)

    return view


async def create_buttons_on_message_queue(interaction: discord.Interaction, page):
    view = create_view_queue(interaction.guild_id, page)

    await my_functions.edit(interaction, view=view)


async def edit_buttons_on_message_queue(response: discord.InteractionMessage, guild_id, page):
    view = create_view_queue(guild_id, page)

    await my_functions.edit_response(response, view=view)
