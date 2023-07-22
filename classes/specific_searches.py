from typing import List

import discord

from classes.music_item import MusicItem
from my_functions import delete_msg


class SpecificSearches:
    def __init__(self, searches: List[MusicItem], shuffle: bool, user: discord.User, message: discord.Message, position: int) -> None:
        self.searches = searches
        self.shuffle = shuffle
        self.user = user
        self.message = message
        self.position = position

    def get_searches(self) -> List[MusicItem]:
        return self.searches

    def get_shuffle(self) -> bool:
        return self.shuffle

    def get_user(self) -> discord.User:
        return self.user

    def get_message(self) -> discord.Message:
        return self.message
    
    def get_position(self) -> int:
        return self.position

    def get_music(self, index: int) -> MusicItem:
        return self.searches[index]

    def set_searches(self, searches: List[MusicItem]) -> None:
        self.searches = searches

    def set_message(self, message: discord.Message) -> None:
        self.message = message
    
    async def reset(self) -> None:
        self.searches = None
        self.shuffle = None
        self.user = None
        await delete_msg(self.message)
        self.message = None
        self.position = None
