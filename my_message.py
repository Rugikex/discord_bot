import discord


async def edit_content(message: discord.Message, content):
    try:
        await message.edit(content=content)
    except discord.errors.HTTPException:
        message = await message.channel.send(content)
    return message


async def delete(message: discord.Message):
    try:
        await message.delete()
    except discord.errors.NotFound:
        pass


async def add_reaction(message: discord.Message, reaction):
    try:
        await message.add_reaction(reaction)
    except discord.errors.NotFound:
        pass
