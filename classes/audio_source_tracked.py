import datetime

import discord


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source: discord.FFmpegPCMAudio):
        self._source = source
        self.count_20ms = 0

    def read(self) -> bytes:
        data = self._source.read()
        if data:
            self.count_20ms += 1
        return data

    @property
    def progress_datetime(self) -> datetime.timedelta:
        return datetime.timedelta(seconds=self.count_20ms * 0.02)

    @property
    def progress_str(self) -> str:
        return str(datetime.timedelta(seconds=self.count_20ms * 0.02)).split(".")[0]
