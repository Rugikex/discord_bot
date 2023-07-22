from typing import Dict
from discord import Client, Intents
from discord.flags import Intents

from classes.server import Server


class MyClient(Client):
    def __init__(self, *, intents: Intents) -> None:
        super().__init__(intents=intents)
        self.servers: Dict[int, Server] = {}
        self.use_youtube_server_id: int = None

    def get_use_youtube_server_id(self) -> int:
        return self.use_youtube_server_id
    
    def set_use_youtube_server_id(self, id: int) -> None:
        self.use_youtube_server_id = id

    def his_using_youtube(self) -> bool:
        return self.use_youtube_server_id is not None

    def add_server(self, id: int) -> None:
        server = Server(id)
        self.servers[id] = server

    def remove_server(self, id: int) -> None:
        self.servers.pop(id, None)

    def get_server(self, id: int) -> Server:
        server = self.servers.get(id)
        if server is None:
            raise Exception("Server not found")
        return server
