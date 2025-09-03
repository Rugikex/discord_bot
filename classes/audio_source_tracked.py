import datetime

import discord


class AudioSourceTracked(discord.AudioSource):
    def __init__(self, source: discord.FFmpegPCMAudio) -> None:
        self._source: discord.FFmpegPCMAudio = source
        self._count_20ms: int = 0

    def read(self) -> bytes:
        data: bytes = self._source.read()
        if data != b"":
            self._count_20ms += 1
        return data

    @property
    def progress_datetime(self) -> datetime.timedelta:
        return datetime.timedelta(seconds=self._count_20ms * 0.02)

    @property
    def progress_str(self) -> str:
        return str(datetime.timedelta(seconds=self._count_20ms * 0.02)).split(
            ".", maxsplit=1
        )[0]
