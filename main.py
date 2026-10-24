import os

import discord
from dotenv import load_dotenv

from classes.my_client import MyClient
import commands


def main() -> None:
    load_dotenv()
    discord_key: str = os.getenv("DISCORD_KEY", "").strip().strip("\"'")
    if not discord_key or discord_key == "None":
        raise KeyError("No DISCORD_KEY found")

    intents: discord.Intents = discord.Intents.default()
    intents.members = True  # Needed to know who is in a voice channel

    client_bot: MyClient = MyClient(
        intents=intents, allowed_mentions=discord.AllowedMentions.none()
    )
    commands.add_commands(client_bot.tree)
    client_bot.run(discord_key)


if __name__ == "__main__":
    main()
