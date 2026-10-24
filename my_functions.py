from __future__ import annotations
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from classes.my_client import MyClient

# Stored in Interaction.extras once the "thinking..." message is used
REPLIED_KEY: str = "replied"


def get_guild_voice_client(guild: discord.Guild | None) -> discord.VoiceClient | None:
    """Voice client of the bot in a guild, None if it isn't connected."""
    # Typed as VoiceProtocol by discord.py, the bot only uses VoiceClient
    voice_client = guild.voice_client if guild is not None else None
    return voice_client if isinstance(voice_client, discord.VoiceClient) else None


async def send_by_channel(
    channel: object,
    content: str,
    permanent: bool = False,
    view: discord.ui.View = discord.utils.MISSING,
    embed: discord.Embed = discord.utils.MISSING,
    file: discord.File = discord.utils.MISSING,
) -> discord.Message | None:
    # None, forums and categories can't receive messages
    if not isinstance(channel, discord.abc.Messageable):
        return None

    try:
        message: discord.Message = await channel.send(
            content, view=view, embed=embed, file=file
        )
    except discord.errors.HTTPException:
        return None

    if not permanent:
        await message.delete(delay=60.0)  # Scheduled, doesn't wait
    return message


def _waits_for_reply(interaction: discord.Interaction[MyClient]) -> bool:
    """True while the "thinking..." message of a slash command is displayed."""
    return (
        interaction.type is discord.InteractionType.application_command
        and interaction.response.is_done()
        and not interaction.extras.get(REPLIED_KEY, False)
    )


async def reply(
    interaction: discord.Interaction[MyClient], content: str, private: bool = False
) -> None:
    """Answer an interaction, visible only by its author if private.

    The first public answer to a slash command replaces its "thinking..."
    message. Public answers are deleted after the guild "delete_replies_after"
    setting (0 to keep them).
    """
    message: discord.InteractionMessage | discord.WebhookMessage | None = None
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(content, ephemeral=private)
            if not private:
                message = await interaction.original_response()
        elif _waits_for_reply(interaction):
            interaction.extras[REPLIED_KEY] = True
            if private:
                # The "thinking..." message is public: replace it by a private one
                await interaction.delete_original_response()
                await interaction.followup.send(content, ephemeral=True)
            else:
                message = await interaction.edit_original_response(content=content)
        else:
            # Button click or second answer
            if private:
                await interaction.followup.send(content, ephemeral=True)
            else:
                message = await interaction.followup.send(content, wait=True)
    except discord.errors.HTTPException:
        # Interaction expired (15 minutes): answer in the channel instead
        await send_by_channel(interaction.channel, content)
        return

    if message is not None and interaction.guild_id is not None:
        delay: int = interaction.client.load_settings(interaction.guild_id)[
            "delete_replies_after"
        ]
        if delay > 0:
            await message.delete(delay=delay)  # Scheduled, doesn't wait


async def finish_interaction(interaction: discord.Interaction[MyClient]) -> None:
    """Remove the "thinking..." message of a command that didn't answer."""
    if not _waits_for_reply(interaction):
        return
    interaction.extras[REPLIED_KEY] = True
    try:
        await interaction.delete_original_response()
    except discord.errors.HTTPException:
        pass


async def edit_message(
    message: discord.Message | None,
    content: str = discord.utils.MISSING,
    embed: discord.Embed | None = discord.utils.MISSING,
    delete_after: float | None = None,
    view: discord.ui.View = discord.utils.MISSING,
    file: discord.File | None = None,
) -> discord.Message | None:
    if message is None:
        return None
    try:
        return await message.edit(
            content=content,
            embed=embed,
            delete_after=delete_after,
            view=view,
            attachments=[file] if file else discord.utils.MISSING,
        )
    except discord.errors.HTTPException:
        # None removes the embed of the edited message: nothing to send
        return await send_by_channel(
            message.channel, content, view=view, embed=embed or discord.utils.MISSING
        )


async def delete_msg(
    message: discord.Message | discord.InteractionMessage | None,
) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except (discord.errors.NotFound, discord.errors.HTTPException):
        pass
