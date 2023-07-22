from typing import List, Union

import discord

from classes.audio_source_tracked import AudioSourceTracked
from classes.current_music_info import CurrentMusicInfo
from classes.music_item import MusicItem
from classes.queue_music import QueueMusic
from classes.specific_searches import SpecificSearches
import my_functions


class Server:
    def __init__(self, id: int) -> None:
        self.id = id
        self.current_music_info: CurrentMusicInfo = None
        self.specifics_searches: SpecificSearches = None
        self.queue_musics: QueueMusic = QueueMusic()
        self.loading_playlist_message: discord.Message = None

    def get_id(self) -> int:
        return self.id
    
    def get_current_music_info(self) -> CurrentMusicInfo:
        return self.current_music_info
    
    def get_specifics_searches(self) -> SpecificSearches:
        return self.specifics_searches
    
    def get_queue_musics(self) -> QueueMusic:
        return self.queue_musics
    
    def get_loading_playlist_message(self) -> discord.Message:
        return self.loading_playlist_message
    
    async def set_current_music_info(self, interaction: discord.Interaction,  music: MusicItem, audio: AudioSourceTracked) -> None:
        message = await my_functions.send_by_channel(
            interaction.channel, f"Now playing {music}.", permanent=True
        )

        if self.current_music_info is None:
            self.current_music_info = CurrentMusicInfo(music, message, audio)
            return
        
        try:
            # FIXME: Il n'y a pas de await a faire attention
            last_message = [message async for message in interaction.channel.history(limit=1)][0]
        except:
            last_message = None

        if last_message is not None and self.current_music_info.has_message() is not None and last_message.id != self.current_music_info.get_message().id:
            await self.current_music_info.delete_message()
        else:
            message = await my_functions.edit_message(self.current_music_info.get_message(), f"Now playing {music}.")
        self.current_music_info.update(music, message, audio)

    def set_specifics_searches(self, specifics_searches: SpecificSearches) -> None:
        self.specifics_searches = specifics_searches

    def set_loading_playlist_message(self, loading_playlist_message: discord.Message) -> None:
        self.loading_playlist_message = loading_playlist_message

    def has_current_music_info(self) -> bool:
        return self.current_music_info is not None
    
    def has_specifics_searches(self) -> bool:
        return self.specifics_searches is not None
    
    async def clear_current_and_queue_messages(self) -> None:
        await self.current_music_info.delete_message()
        await self.queue_musics.delete_message()
        self.current_music_info = None

    async def disconnect(self) -> None:
        await self.clear_current_and_queue_messages()
        await my_functions.delete_msg(self.loading_playlist_message)
        await self.specifics_searches.reset()
        # TODO: Delete other message