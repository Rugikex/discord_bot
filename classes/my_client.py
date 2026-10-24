from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from discord import Client, utils

from classes.my_command_tree import MyCommandTree
from classes.guild_player import GuildPlayer
from constants import BASE_DIR, DEFAULT_SETTINGS
from logger_setup import my_logger
import my_functions

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from discord import (
        AllowedMentions,
        Guild,
        Intents,
        Interaction,
        Member,
        VoiceClient,
        VoiceState,
    )
    from discord.app_commands import Command, ContextMenu

SETTINGS_FOLDER: Path = BASE_DIR / "guild_settings"
BLACKLIST_FILE: Path = BASE_DIR / "blacklist.txt"


class MyClient(Client):
    def __init__(
        self, *, intents: Intents, allowed_mentions: AllowedMentions | None = None
    ) -> None:
        super().__init__(intents=intents, allowed_mentions=allowed_mentions)
        self.tree: MyCommandTree = MyCommandTree(self)
        # Only the guilds where the bot is connected to a voice channel
        self._players: dict[int, GuildPlayer] = {}
        self._blacklist: set[int] = self._get_blacklist()
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def setup_hook(self) -> None:
        # Called once at login, unlike on_ready which fires on every reconnection
        await self.tree.sync()

    async def on_app_command_completion(
        self, interaction: Interaction, command: Command | ContextMenu
    ) -> None:
        await my_functions.finish_interaction(interaction)

    async def on_ready(self) -> None:
        self.init_guild_settings([guild.id for guild in self.guilds])

        my_logger.info(
            "Logged in as %s to %s.", self.user, [guild.name for guild in self.guilds]
        )

    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ) -> None:
        """Disconnect the bot if alone in a voice channel or if kicked."""
        guild_id: int = member.guild.id
        # Mute, deafen, stream... or the bot is not playing in this server
        if before.channel == after.channel or not self.player_exists(guild_id):
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

        player: GuildPlayer | None = self.find_player(guild_id)
        if player is None:
            if voice_client is not None:
                await voice_client.disconnect()
            return
        if player.is_disconnected:
            return

        self.remove_player(guild_id)
        player.disconnect()
        await player.track_queue.clear_queue(None)

        if voice_client is not None:
            voice_client.stop()
            await asyncio.sleep(1.0)  # Wait for the track to stop
            await voice_client.disconnect()

        # Always delete the messages ("Playing", queue...), even after a kick
        await player.clear()

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

    def init_guild_settings(self, guild_ids: list[int]) -> None:
        """Create or complete the settings file of each guild.

        Files of guilds the bot has left are kept, in case it is invited again.
        """
        for guild_id in guild_ids:
            settings: dict[str, Any] = self.load_settings(guild_id)
            if self._read_settings_file(guild_id) != settings:
                self.save_settings(guild_id, settings)

    def player_exists(self, guild_id: int) -> bool:
        return guild_id in self._players

    def find_player(self, guild_id: int | None) -> GuildPlayer | None:
        if guild_id is None:
            return None
        return self._players.get(guild_id)

    def get_player(self, guild_id: int | None) -> GuildPlayer:
        if guild_id is None:
            raise ValueError("Guild ID must not be None")

        player: GuildPlayer | None = self._players.get(guild_id)
        if player is None:
            raise KeyError("Guild player not found")
        return player

    @staticmethod
    def _settings_path(guild_id: int) -> Path:
        return SETTINGS_FOLDER / f"{guild_id}.json"

    def _read_settings_file(self, guild_id: int) -> dict[str, Any]:
        file_path: Path = self._settings_path(guild_id)
        if not file_path.exists():
            return {}
        try:
            settings: Any = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return settings if isinstance(settings, dict) else {}

    def load_settings(self, guild_id: int) -> dict[str, Any]:
        """Settings of the guild, completed with the default values."""
        settings: dict[str, Any] = self._read_settings_file(guild_id)
        return {
            key: settings.get(key, copy.deepcopy(value))
            for key, value in DEFAULT_SETTINGS.items()
        }

    def save_settings(self, guild_id: int, settings: dict[str, Any]) -> None:
        SETTINGS_FOLDER.mkdir(exist_ok=True)
        self._settings_path(guild_id).write_text(
            json.dumps(settings, indent=4, ensure_ascii=False), encoding="utf-8"
        )

    def update_setting(self, guild_id: int, key: str, value: Any) -> None:
        settings: dict[str, Any] = self.load_settings(guild_id)
        settings[key] = value
        self.save_settings(guild_id, settings)

        # A connected player keeps its default platform in memory
        player: GuildPlayer | None = self.find_player(guild_id)
        if player is not None and key == "default_platform":
            player.default_platform = value

    def add_player(self, guild_id: int | None) -> None:
        if guild_id is None:
            raise ValueError("Guild ID must not be None")

        settings: dict[str, Any] = self.load_settings(guild_id)
        player: GuildPlayer = GuildPlayer(
            guild_id,
            settings["default_platform"],
            settings["default_tracks"],
            settings["welcome_track"],
        )
        self._players[guild_id] = player

    def remove_player(self, guild_id: int) -> None:
        self._players.pop(guild_id, None)

    @property
    def blacklist(self) -> set[int]:
        return self._blacklist
