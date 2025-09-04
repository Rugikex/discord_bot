from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord import User, Member
    from datetime import timedelta


class Track:
    def __init__(
        self, title: str, duration: timedelta, link: str, requester: User | Member
    ) -> None:
        self._title: str = title
        self._duration: timedelta = duration
        self._link: str = link
        self._requester: User | Member = requester

    def __str__(self) -> str:
        return f"{self._title} ({self._duration})"

    @property
    def title(self) -> str:
        return self._title

    @property
    def duration(self) -> timedelta | str:
        return self._duration

    @property
    def link(self) -> str:
        return self._link

    @property
    def requester(self) -> User | Member:
        return self._requester
