from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import timedelta


class Track:
    def __init__(self, title: str, duration: timedelta | None, link: str):
        self._title = title
        self._duration = duration if duration is not None else "???"
        self._link = link

    def __str__(self) -> str:
        return f"{self.title} ({self.duration})"

    @property
    def title(self) -> str:
        return self._title

    @property
    def duration(self) -> timedelta | str:
        return self._duration

    @property
    def link(self) -> str:
        return self._link
