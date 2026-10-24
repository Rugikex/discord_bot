from __future__ import annotations
import datetime
from typing import Any

import pytest

from classes.track import Track


def make_track(title: str) -> Track:
    return Track(title, datetime.timedelta(seconds=60), title, "youtube", None)  # type: ignore[arg-type]


class Replies:
    """Records the answers sent with my_functions.reply."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, bool]] = []

    async def __call__(
        self, interaction: Any, content: str, private: bool = False
    ) -> None:
        self.messages.append((content, private))


@pytest.fixture
def replies(monkeypatch: pytest.MonkeyPatch) -> Replies:
    import my_functions

    recorder = Replies()
    monkeypatch.setattr(my_functions, "reply", recorder)
    return recorder
