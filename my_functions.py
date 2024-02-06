import asyncio
import discord
from typing import Union


import globals_var


InteractionChannel = Union[
    discord.VoiceChannel,
    discord.StageChannel,
    discord.TextChannel,
    discord.ForumChannel,
    discord.CategoryChannel,
    discord.Thread,
    discord.DMChannel,
    discord.GroupChannel,
]


async def get_response(interaction: discord.Interaction):
    try:
        return await interaction.original_response()
    except discord.errors.NotFound:
        return interaction.response


async def send_by_channel(
    channel: InteractionChannel | None,
    content: str,
    permanent: bool = False,
    view: discord.ui.View | None = None,
) -> discord.Message | None:
    if not channel:
        return None
    delete_after = None if permanent else 60.0

    if not hasattr(channel, "send"):
        return None

    try:
        return await channel.send(content, delete_after=delete_after, view=view)
    except discord.errors.HTTPException:
        return None


async def send_by_interaction(
    interaction: discord.Interaction,
    content: str,
    delete_after: float | None = None,
    view: discord.ui.View = discord.utils.MISSING,
):
    try:
        await interaction.response.send_message(
            content, delete_after=delete_after, view=view, ephemeral=True
        )
    except discord.errors.InteractionResponded:
        await edit_interaction(interaction, content=content, view=view)
    except discord.errors.HTTPException:
        await send_by_channel(interaction.channel, content, view=view)


async def edit_interaction(
    interaction: discord.Interaction,
    content: str = discord.utils.MISSING,
    view: discord.ui.View = discord.utils.MISSING,
):
    try:
        response = await get_response(interaction)
        if isinstance(response, discord.InteractionResponse):
            if response.type is None:
                await send_by_channel(interaction.channel, content, view=view)
            else:
                await response.edit_message(content=content, view=view)
        else:
            await response.edit(content=content, view=view)
    except (discord.errors.HTTPException, discord.errors.InteractionResponded):
        await send_by_channel(interaction.channel, content, view=view)


async def edit_message(
    message: discord.Message | None,
    content: str = discord.utils.MISSING,
    view: discord.ui.View = discord.utils.MISSING,
) -> discord.Message | None:
    if not message:
        return None
    try:
        return await message.edit(content=content, view=view)
    except discord.errors.HTTPException:
        return await send_by_channel(message.channel, content, view=view)


async def edit_response(
    response: discord.InteractionMessage,
    content: str = discord.utils.MISSING,
    view: discord.ui.View = discord.utils.MISSING,
):
    try:
        await response.edit(content=content, view=view)
    except discord.errors.HTTPException:
        pass


async def delete_msg(message: discord.Message | discord.InteractionMessage | None):
    if message is None or isinstance(message, discord.InteractionResponse):
        return
    try:
        await message.delete()
    except (discord.errors.NotFound, discord.errors.HTTPException):
        pass


async def disconnect_bot(
    voice_client: discord.VoiceClient, guild_id: int | None
) -> None:
    if not guild_id:
        return

    server = globals_var.client_bot.get_server(guild_id)
    if server.get_is_disconnect():
        return
    server.being_disconnect()
    await server.get_queue_musics().clear_queue(None)

    voice_client.stop()
    await asyncio.sleep(1.0)  # Wait for the music to stop

    await voice_client.disconnect()
    await server.disconnect()

    if globals_var.client_bot.get_use_youtube_server_id() == guild_id:
        globals_var.client_bot.set_use_youtube_server_id(None)

    globals_var.client_bot.remove_server(guild_id)

    globals_var.my_logger.info(f"Bot disconnects to {voice_client.guild.name}.")


# Not use
async def add_reaction(interaction: discord.Interaction, reaction):
    try:
        interaction_message = await interaction.original_response()
        await interaction_message.add_reaction(reaction)
    except discord.errors.NotFound:
        pass


def user_is_blacklisted(user_id: int) -> bool:
    return user_id in globals_var.client_bot.blacklist
