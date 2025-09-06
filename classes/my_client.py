from __future__ import annotations
from io import TextIOWrapper
import os
from typing import TYPE_CHECKING

from discord import Client

from classes.server import Server

if TYPE_CHECKING:
    from discord import Intents


class MyClient(Client):
    def __init__(self, *, intents: Intents) -> None:
        super().__init__(intents=intents)
        self._servers: dict[int, Server] = {}
        self._server_id_using_youtube: int | None = None
        self._blacklist: set[int] = self._get_blacklist()

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
        server: Server = Server(server_id)
        self._servers[server_id] = server

    def remove_server(self, server_id: int) -> None:
        self._servers.pop(server_id, None)

    @property
    def server_id_using_youtube(self) -> int | None:
        return self._server_id_using_youtube

    @server_id_using_youtube.setter
    def server_id_using_youtube(self, value: int | None) -> None:
        self._server_id_using_youtube = value

    @property
    def blacklist(self) -> set[int]:
        return self._blacklist
