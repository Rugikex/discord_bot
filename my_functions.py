import discord


async def send_by_channel(channel, content):
    if not channel:
        return
    try:
        return await channel.send(content)
    except discord.errors.HTTPException:
        pass


async def send(interaction: discord.Interaction, content):
    try:
        await interaction.response.send_message(content)
    except discord.errors.InteractionResponded:
        await edit(interaction, content=content)
    except discord.errors.HTTPException:
        pass


async def edit(interaction: discord.Interaction, content=discord.utils.MISSING, view=discord.utils.MISSING):
    try:
        response = await interaction.original_response()
        await response.edit(content=content, view=view)
    except discord.errors.HTTPException:
        await send_by_channel(interaction.channel, content)


async def edit_response(response: discord.InteractionMessage, content=discord.utils.MISSING, view=discord.utils.MISSING):
    try:
        await response.edit(content=content, view=view)
    except discord.errors.HTTPException:
        pass


# message can be discord.Message or discord.InteractionMessage
async def delete_msg(message):
    try:
        await message.delete()
    except discord.errors.NotFound:
        pass


async def add_reaction(interaction: discord.Interaction, reaction):
    try:
        interaction_message = await interaction.original_response()
        await interaction_message.add_reaction(reaction)
    except discord.errors.NotFound:
        pass
