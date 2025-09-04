from __future__ import annotations
import asyncio
from typing import Union, TYPE_CHECKING

import discord

import globals_var

if TYPE_CHECKING:
    from classes.server import Server
    from classes.track import Track


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


async def get_response(
    interaction: discord.Interaction,
) -> discord.InteractionResponse | discord.Message:
    try:
        return await interaction.original_response()
    except discord.errors.NotFound:
        return interaction.response


async def send_by_channel(
    channel: InteractionChannel | None,
    content: str,
    permanent: bool = False,
    view: discord.ui.View | None = None,
    embed: discord.Embed | None = None,
    file: discord.File | None = None,
) -> discord.Message | None:
    if channel is None:
        return None
    delete_after: float | None = None if permanent else 60.0

    if not hasattr(channel, "send"):
        return None

    try:
        return await channel.send(
            content, delete_after=delete_after, view=view, embed=embed, file=file
        )
    except discord.errors.HTTPException:
        return None


async def send_by_interaction(
    interaction: discord.Interaction,
    content: str,
    delete_after: float | None = None,
    view: discord.ui.View = discord.utils.MISSING,
) -> None:
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
        response: discord.InteractionResponse | discord.Message = await get_response(
            interaction
        )
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
    embed: discord.Embed | None = discord.utils.MISSING,
    delete_after: float | None = None,
    view: discord.ui.View = discord.utils.MISSING,
) -> discord.Message | None:
    if message is None:
        return None
    try:
        return await message.edit(
            content=content, embed=embed, delete_after=delete_after, view=view
        )
    except discord.errors.HTTPException:
        return await send_by_channel(message.channel, content, view=view, embed=embed)


async def edit_response(
    response: discord.InteractionMessage,
    content: str = discord.utils.MISSING,
    view: discord.ui.View = discord.utils.MISSING,
) -> None:
    try:
        await response.edit(content=content, view=view)
    except discord.errors.HTTPException:
        pass


async def delete_msg(
    message: discord.Message | discord.InteractionMessage | None,
) -> None:
    if message is None or isinstance(message, discord.InteractionResponse):
        return
    try:
        await message.delete()
    except (discord.errors.NotFound, discord.errors.HTTPException):
        pass


async def disconnect_bot(
    voice_client: discord.VoiceClient, guild_id: int | None
) -> None:
    if guild_id is None:
        return

    server: Server = globals_var.client_bot.get_server(guild_id)
    if server.is_disconnected:
        return

    globals_var.client_bot.remove_server(guild_id)
    server.disconnect()
    await server.track_queue.clear_queue(None)

    voice_client.stop()
    await asyncio.sleep(1.0)  # Wait for the track to stop

    await voice_client.disconnect()
    await server.clear()

    if globals_var.client_bot.server_id_using_youtube == guild_id:
        globals_var.client_bot.server_id_using_youtube = None

    globals_var.my_logger.info(f"Bot disconnects to {voice_client.guild.name}.")


def user_is_blacklisted(user_id: int) -> bool:
    return user_id in globals_var.client_bot.blacklist


def create_embed(track: Track, is_looping: bool) -> tuple[discord.Embed, discord.File]:
    """Create a discord embed and a discord file with the youtube logo."""
    youtube_logo_name: str = "youtube-logo.png"

    embed: discord.Embed = discord.Embed(
        title=track.title, url=track.link, color=discord.Color.red()
    )

    # TODO embed.set_footer(text="Requested by user")
    embed.set_author(name="Playing", icon_url=f"attachment://{youtube_logo_name}")
    loop_str: str = "✔️" if is_looping else "❌"
    embed.description = f"Duration: {track.duration}\nLoop: {loop_str}"
    file: discord.File = discord.File(
        f"assets/{youtube_logo_name}", filename=youtube_logo_name
    )

    return embed, file


# Not use
async def add_reaction(interaction: discord.Interaction, reaction) -> None:
    try:
        interaction_message: discord.InteractionMessage = (
            await interaction.original_response()
        )
        await interaction_message.add_reaction(reaction)
    except discord.errors.NotFound:
        pass
