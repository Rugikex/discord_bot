from __future__ import annotations
import asyncio
from io import TextIOWrapper
import json
import os
from typing import TYPE_CHECKING, Any

from discord import Client, utils

from classes.my_command_tree import MyCommandTree
from classes.server import Server
from constants import SAVE_SETTINGS_TIMER, DEFAULT_SETTINGS
from logger_setup import my_logger

if TYPE_CHECKING:
    from discord import AllowedMentions, Intents, Member, VoiceClient, VoiceState


class MyClient(Client):
    def __init__(
        self, *, intents: Intents, allowed_mentions: AllowedMentions | None = None
    ) -> None:
        super().__init__(intents=intents, allowed_mentions=allowed_mentions)
        self.tree: MyCommandTree = MyCommandTree(self)
        self._servers: dict[int, Server] = {}
        self._blacklist: set[int] = self._get_blacklist()
        self._diff_settings: dict[int, Any] = {}
        self._is_saving_settings: bool = False

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

    async def periodic_save_settings(self) -> None:
        while True:
            await asyncio.sleep(SAVE_SETTINGS_TIMER)
            if self._diff_settings:
                self._save_settings()

    def _save_settings(self) -> None:
        current_diff: dict[int, Any] = self._diff_settings.copy()
        self._diff_settings.clear()
        for server_id, diff in current_diff.items():
            file_path = f"server_settings/{server_id}.json"

            full_settings = {}
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        full_settings = json.load(file)
                except json.JSONDecodeError:
                    full_settings = DEFAULT_SETTINGS.copy()

            full_settings.update(diff)

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(full_settings, file, indent=4, ensure_ascii=False)

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
        os.makedirs("server_settings", exist_ok=True)

        for file in os.listdir("server_settings"):
            try:
                server_id: int = int(file.split(".")[0])
            except ValueError:
                continue
            if server_id not in server_ids:
                os.remove(f"server_settings/{file}")
                continue
            server_ids.remove(server_id)

            file_path: str = f"server_settings/{server_id}.json"

            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(DEFAULT_SETTINGS, file, indent=4)
                continue

            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    settings: dict[str, Any] = json.load(file)
                except json.JSONDecodeError:
                    settings = DEFAULT_SETTINGS.copy()

            previous_keys: set[str] = set(settings.keys())
            for key, value in DEFAULT_SETTINGS.items():
                settings.setdefault(key, value)

            settings = {key: settings[key] for key in DEFAULT_SETTINGS.keys()}
            if set(settings.keys()) != previous_keys:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(settings, file, indent=4)

        for server_id in server_ids:
            with open(
                f"server_settings/{server_id}.json", "w", encoding="utf-8"
            ) as file:
                json.dump(DEFAULT_SETTINGS, file, indent=4)

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

    def load_settings(self, server_id: int) -> dict[str, Any]:
        settings: dict[str, Any] = {}
        file_path: str = f"server_settings/{server_id}.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    pass

        for key, value in DEFAULT_SETTINGS.items():
            settings.setdefault(key, value)
        return settings

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
