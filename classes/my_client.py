from __future__ import annotations
import asyncio
import copy
from io import TextIOWrapper
import json
import os
from typing import TYPE_CHECKING, Any

from discord import Client, utils

from classes.my_command_tree import MyCommandTree
from classes.server import Server
from constants import DEFAULT_SETTINGS
from logger_setup import my_logger

if TYPE_CHECKING:
    from discord import AllowedMentions, Intents, Member, VoiceClient, VoiceState

SETTINGS_FOLDER: str = "server_settings"


class MyClient(Client):
    def __init__(
        self, *, intents: Intents, allowed_mentions: AllowedMentions | None = None
    ) -> None:
        super().__init__(intents=intents, allowed_mentions=allowed_mentions)
        self.tree: MyCommandTree = MyCommandTree(self)
        self._servers: dict[int, Server] = {}
        self._blacklist: set[int] = self._get_blacklist()

    async def setup_hook(self) -> None:
        # Called once at login, unlike on_ready which fires on every reconnection
        await self.tree.sync()

    async def on_ready(self) -> None:
        self.init_server_settings([guild.id for guild in self.guilds])

        my_logger.info(
            "Logged in as %s to %s.", self.user, [guild.name for guild in self.guilds]
        )

    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ) -> None:
        """Disconnect the bot if alone in a voice channel or if kicked."""
        voice_client: VoiceClient | None = utils.get(
            self.voice_clients, guild=member.guild
        )
        if voice_client is None or before.channel is None:
            return

        if not self.server_exists(member.guild.id):
            return

        if (
            member != self.user
            and self.user in before.channel.members
            and len(before.channel.members) == 1
        ):
            self.loop.create_task(self.disconnect_bot(voice_client, member.guild.id))
            return

        if (
            member == self.user
            and after.channel
            and before.channel is not after.channel
        ):
            if len(after.channel.members) == 1:
                self.loop.create_task(
                    self.disconnect_bot(voice_client, member.guild.id)
                )
            else:
                voice_client.resume()
            return

        if (
            member == self.user
            and not after.channel
            and len(before.channel.members) != 0
        ):
            self.loop.create_task(self.disconnect_bot(voice_client, member.guild.id))
            return

    async def disconnect_bot(
        self, voice_client: VoiceClient, guild_id: int | None
    ) -> None:
        if guild_id is None:
            return

        server: Server | None = self.find_server(guild_id)
        if server is None:
            await voice_client.disconnect()
            return
        if server.is_disconnected:
            return

        self.remove_server(guild_id)
        server.disconnect()
        await server.track_queue.clear_queue(None)

        voice_client.stop()
        await asyncio.sleep(1.0)  # Wait for the track to stop

        await voice_client.disconnect()
        await server.clear()

        my_logger.info("Bot disconnects to %s.", voice_client.guild.name)

    def _get_blacklist(self) -> set[int]:
        if not os.path.exists("blacklist.txt"):
            return set()

        file: TextIOWrapper
        with open("blacklist.txt", "r", encoding="utf-8") as file:
            result: set[int] = set()
            line: str
            for line in file.readlines():
                line = line.strip()
                if line == "":
                    continue
                try:
                    result.add(int(line))
                except ValueError:
                    pass

            return result

    def init_server_settings(self, server_ids: list[int]) -> None:
        """Create or complete the settings file of each server.

        Files of servers the bot has left are kept, in case it is invited again.
        """
        for server_id in server_ids:
            settings: dict[str, Any] = self.load_settings(server_id)
            if self._read_settings_file(server_id) != settings:
                self.save_settings(server_id, settings)

    def server_exists(self, server_id: int) -> bool:
        return server_id in self._servers

    def find_server(self, server_id: int | None) -> Server | None:
        if server_id is None:
            return None
        return self._servers.get(server_id)

    def get_server(self, server_id: int | None) -> Server:
        if server_id is None:
            raise ValueError("Server ID must not be None")

        server: Server | None = self._servers.get(server_id)
        if server is None:
            raise KeyError("Server not found")
        return server

    def _read_settings_file(self, server_id: int) -> dict[str, Any]:
        file_path: str = f"{SETTINGS_FOLDER}/{server_id}.json"
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                settings: Any = json.load(file)
            except json.JSONDecodeError:
                return {}
        return settings if isinstance(settings, dict) else {}

    def load_settings(self, server_id: int) -> dict[str, Any]:
        """Settings of the server, completed with the default values."""
        settings: dict[str, Any] = self._read_settings_file(server_id)
        return {
            key: settings.get(key, copy.deepcopy(value))
            for key, value in DEFAULT_SETTINGS.items()
        }

    def save_settings(self, server_id: int, settings: dict[str, Any]) -> None:
        os.makedirs(SETTINGS_FOLDER, exist_ok=True)
        with open(f"{SETTINGS_FOLDER}/{server_id}.json", "w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4, ensure_ascii=False)

    def update_setting(self, server_id: int, key: str, value: Any) -> None:
        settings: dict[str, Any] = self.load_settings(server_id)
        settings[key] = value
        self.save_settings(server_id, settings)

        # A connected server keeps its default platform in memory
        server: Server | None = self.find_server(server_id)
        if server is not None and key == "default_platform":
            server.default_platform = value

    def add_server(self, server_id: int | None) -> None:
        if server_id is None:
            raise ValueError("Server ID must not be None")

        settings: dict[str, Any] = self.load_settings(server_id)
        server: Server = Server(
            server_id,
            settings["default_platform"],
            settings["default_tracks"],
            settings["welcome_track"],
        )
        self._servers[server_id] = server

    def remove_server(self, server_id: int) -> None:
        self._servers.pop(server_id, None)

    @property
    def blacklist(self) -> set[int]:
        return self._blacklist
