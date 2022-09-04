import discord


async def send_by_channel(channel, content):
    if not channel:
        return
    try:
        await channel.send(content)
    except discord.errors.HTTPException:
        pass


async def send(interaction: discord.Interaction, content, delete_after=None):
    try:
        await interaction.response.send_message(content)
    except discord.errors.HTTPException:
        pass


async def edit_content(interaction: discord.Interaction, content):
    try:
        interaction_message = await interaction.original_response()
        await interaction_message.edit(content=content)
    except discord.errors.HTTPException:
        await send_by_channel(interaction.channel, content)


async def delete(message: discord.Message):
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
