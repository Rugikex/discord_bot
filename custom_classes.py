import datetime

import discord


class MusicItem:
    def __init__(self, platform, title, duration, link):
        self.platform = platform
        self.title = title
        self.duration = duration
        self.link = link

    def __str__(self):
        return f"{self.title} ({self.duration})"


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source):
        self._source = source
        self.count_20ms = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count_20ms += 1
        return data

    @property
    def progress_datetime(self) -> datetime:
        return datetime.timedelta(seconds=self.count_20ms * 0.02)

    @property
    def progress_str(self) -> str:
        return str(datetime.timedelta(seconds=self.count_20ms * 0.02)).split('.')[0]

