import discord

from classes.audio_source_tracked import AudioSourceTracked
from classes.music_item import MusicItem
from my_functions import delete_msg


class CurrentMusicInfo:
    def __init__(self, music: MusicItem, message: discord.Message, audio: AudioSourceTracked) -> None:
        self.music = music
        self.message = message
        self.audio = audio

    def get_music(self) -> MusicItem:
        return self.music
    
    def get_message(self) -> discord.Message:
        return self.message
    
    def get_audio(self) -> AudioSourceTracked:
        return self.audio

    async def delete_message(self) -> None:
        await delete_msg(self.message)
        self.message = None
    
    def has_message(self) -> bool:
        return self.message is not None

    def update(self, music: MusicItem, message: discord.Message, audio: AudioSourceTracked) -> None:
        self.music = music
        self.message = message
        self.audio = audio
