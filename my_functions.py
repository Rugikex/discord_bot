import discord

import globals_var


async def get_response(interaction: discord.Interaction):
    try:
        return await interaction.original_response()
    except discord.errors.NotFound:
        return interaction.response


async def send_by_channel(channel: discord.GroupChannel, content: str, permanent: bool = False,
                          view: discord.ui.View = None) -> discord.Message | None:
    if not channel:
        return None
    delete_after = None if permanent else 60.0
    try:
        return await channel.send(content, delete_after=delete_after, view=view)
    except discord.errors.HTTPException:
        return None


async def send_by_interaction(interaction: discord.Interaction, content: str, delete_after: float = None,
                              view: discord.ui.View = discord.utils.MISSING):
    if delete_after is None:
        delete_after = (interaction.expires_at - interaction.created_at).total_seconds() - 600.0
    try:
        await interaction.response.send_message(content, delete_after=delete_after, view=view, ephemeral=True)
    except discord.errors.InteractionResponded:
        await edit_interaction(interaction, content=content, view=view)
    except discord.errors.HTTPException:
        await send_by_channel(interaction.channel, content, view=view)


async def edit_interaction(interaction: discord.Interaction, content: str = discord.utils.MISSING,
                           view: discord.ui.View = discord.utils.MISSING):
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


async def edit_message(message: discord.Message, content: str = discord.utils.MISSING,
                       view: discord.ui.View = discord.utils.MISSING) -> discord.Message:
    try:
        return await message.edit(content=content, view=view)
    except discord.errors.HTTPException:
        return await send_by_channel(message.channel, content, view=view)


async def edit_response(response: discord.InteractionMessage, content: str = discord.utils.MISSING,
                        view: discord.ui.View = discord.utils.MISSING):
    try:
        await response.edit(content=content, view=view)
    except discord.errors.HTTPException:
        pass


async def delete_msg(message: discord.Message | discord.InteractionMessage):
    if message is None or isinstance(message, discord.InteractionResponse):
        return
    try:
        await message.delete()
    except (discord.errors.NotFound, discord.errors.HTTPException):
        pass


async def disconnect_bot(voice_client: discord.VoiceClient, guild_id: int):
    globals_var.queues_musics.pop(guild_id, None)
    voice_client.stop()
    await voice_client.disconnect()
    if guild_id in globals_var.current_music:
        await delete_msg(globals_var.current_music[guild_id]['message'])
    if guild_id in globals_var.queues_message:
        await delete_msg(globals_var.queues_message[guild_id])
    if guild_id in globals_var.loading_playlist_message:
        await delete_msg(globals_var.loading_playlist_message[guild_id])
    globals_var.queues_message.pop(guild_id, None)
    globals_var.current_music.pop(guild_id, None)
    globals_var.loading_playlist_message.pop(guild_id, None)
    if guild_id in globals_var.current_music:
        await delete_msg(globals_var.specifics_searches[guild_id]['message'])
    globals_var.specifics_searches.pop(guild_id, None)
    if globals_var.queue_request_youtube == guild_id:
        globals_var.queue_request_youtube = None

    globals_var.my_logger.info(f"Bot disconnects to {voice_client.guild.name}.")


# Not use
async def add_reaction(interaction: discord.Interaction, reaction):
    try:
        interaction_message = await interaction.original_response()
        await interaction_message.add_reaction(reaction)
    except discord.errors.NotFound:
        pass
