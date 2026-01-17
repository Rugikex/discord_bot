from __future__ import annotations
import asyncio
from io import TextIOWrapper
import json
import os
from typing import TYPE_CHECKING, Any

from discord import Client

from classes.server import Server
from constants import SAVE_SETTINGS_TIMER, DEFAULT_SETTINGS

if TYPE_CHECKING:
    from discord import Intents


class MyClient(Client):
    def __init__(self, *, intents: Intents) -> None:
        super().__init__(intents=intents)
        self._servers: dict[int, Server] = {}
        self._blacklist: set[int] = self._get_blacklist()
        self._is_using_youtube: int | None = None
        self._diff_settings: dict[int, Any] = {}
        self._is_saving_settings: bool = False

    async def periodic_save_settings(self) -> None:
        while True:
            await asyncio.sleep(SAVE_SETTINGS_TIMER)
            if self._diff_settings:
                self._save_settings()

    def _save_settings(self) -> None:
        for server_id, settings in self._diff_settings.items():
            file_path: str = f"server_settings/{server_id}.json"
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(settings, file, indent=4)
        self._diff_settings.clear()

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

    def get_server(self, server_id: int | None) -> Server:
        if server_id is None:
            raise ValueError("Server ID must not be None")

        server: Server | None = self._servers.get(server_id)
        if server is None:
            raise KeyError("Server not found")
        return server

    def add_server(self, server_id: int | None) -> None:
        if server_id is None:
            raise ValueError("Server ID must not be None")

        file_path: str = f"server_settings/{server_id}.json"
        settings: dict[str, Any]
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    settings: dict[str, Any] = json.load(file)
                except json.JSONDecodeError:
                    settings = DEFAULT_SETTINGS.copy()
        else:
            settings = DEFAULT_SETTINGS.copy()

        server: Server = Server(
            server_id, settings["default_platform"], settings["default_tracks"]
        )
        self._servers[server_id] = server

    def remove_server(self, server_id: int) -> None:
        self._servers.pop(server_id, None)

    @property
    def blacklist(self) -> set[int]:
        return self._blacklist

    @property
    def is_using_youtube(self) -> int | None:
        return self._is_using_youtube

    @is_using_youtube.setter
    def is_using_youtube(self, value: int | None) -> None:
        self._is_using_youtube = value
