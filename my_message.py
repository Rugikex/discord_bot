import discord


async def send(message: discord.Message, content, delete_after=None):
    try:
        return await message.channel.send(content, delete_after=delete_after)
    except discord.errors.HTTPException:
        pass


async def edit_content(message: discord.Message, content):
    try:
        await message.edit(content=content)
    except discord.errors.HTTPException:
        message = await send(message, content)
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
