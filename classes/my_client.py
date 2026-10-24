from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from discord import Client, utils

from classes.my_command_tree import MyCommandTree
from classes.server import Server
from constants import BASE_DIR, DEFAULT_SETTINGS
from logger_setup import my_logger

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from discord import (
        AllowedMentions,
        Guild,
        Intents,
        Member,
        VoiceClient,
        VoiceState,
    )

SETTINGS_FOLDER: Path = BASE_DIR / "server_settings"
BLACKLIST_FILE: Path = BASE_DIR / "blacklist.txt"


class MyClient(Client):
    def __init__(
        self, *, intents: Intents, allowed_mentions: AllowedMentions | None = None
    ) -> None:
        super().__init__(intents=intents, allowed_mentions=allowed_mentions)
        self.tree: MyCommandTree = MyCommandTree(self)
        self._servers: dict[int, Server] = {}
        self._blacklist: set[int] = self._get_blacklist()
        self._background_tasks: set[asyncio.Task[None]] = set()

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
        guild_id: int = member.guild.id
        # Mute, deafen, stream... or the bot is not playing in this server
        if before.channel == after.channel or not self.server_exists(guild_id):
            return

        # Already None if discord.py has handled a kick before this event
        voice_client: VoiceClient | None = utils.get(
            self.voice_clients, guild=member.guild
        )

        if member == self.user:
            if after.channel is None or len(after.channel.members) == 1:
                # Kicked, disconnected by hand or moved to an empty channel
                self._run_in_background(self.disconnect_bot(voice_client, guild_id))
            elif voice_client is not None:
                voice_client.resume()  # The audio is paused during the move
            return

        # Another member left the bot's channel
        if (
            voice_client is not None
            and before.channel == voice_client.channel
            and len(before.channel.members) == 1
        ):
            self._run_in_background(self.disconnect_bot(voice_client, guild_id))

    def _run_in_background(self, coro: Coroutine[Any, Any, None]) -> None:
        # asyncio only keeps a weak reference to tasks: keep one until they end
        task: asyncio.Task[None] = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def disconnect_bot(
        self, voice_client: VoiceClient | None, guild_id: int | None
    ) -> None:
        if guild_id is None:
            return

        server: Server | None = self.find_server(guild_id)
        if server is None:
            if voice_client is not None:
                await voice_client.disconnect()
            return
        if server.is_disconnected:
            return

        self.remove_server(guild_id)
        server.disconnect()
        await server.track_queue.clear_queue(None)

        if voice_client is not None:
            voice_client.stop()
            await asyncio.sleep(1.0)  # Wait for the track to stop
            await voice_client.disconnect()

        # Always delete the messages ("Playing", queue...), even after a kick
        await server.clear()

        guild: Guild | None = self.get_guild(guild_id)
        my_logger.info("Bot disconnects to %s.", guild.name if guild else guild_id)

    def _get_blacklist(self) -> set[int]:
        if not BLACKLIST_FILE.exists():
            return set()

        result: set[int] = set()
        line: str
        for line in BLACKLIST_FILE.read_text(encoding="utf-8").splitlines():
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

    @staticmethod
    def _settings_path(server_id: int) -> Path:
        return SETTINGS_FOLDER / f"{server_id}.json"

    def _read_settings_file(self, server_id: int) -> dict[str, Any]:
        file_path: Path = self._settings_path(server_id)
        if not file_path.exists():
            return {}
        try:
            settings: Any = json.loads(file_path.read_text(encoding="utf-8"))
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
        SETTINGS_FOLDER.mkdir(exist_ok=True)
        self._settings_path(server_id).write_text(
            json.dumps(settings, indent=4, ensure_ascii=False), encoding="utf-8"
        )

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
