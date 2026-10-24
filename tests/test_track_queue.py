from __future__ import annotations
import asyncio
from typing import Any

import pytest

from classes.track_queue import TrackQueue
import voice_gestion

from .conftest import Replies, make_track

INTERACTION: Any = object()


def make_queue(*titles: str) -> TrackQueue:
    queue = TrackQueue()
    for title in titles:
        asyncio.run(
            queue.add_in_queue(INTERACTION, [make_track(title)], None, "", False)
        )
    return queue


def titles(queue: TrackQueue) -> list[str]:
    return [track.title for track in queue._tracks]


@pytest.fixture
def connected(monkeypatch: pytest.MonkeyPatch) -> None:
    """remove_tracks first checks that the bot is playing."""

    async def check_voice_client(interaction: Any) -> object:
        return object()

    monkeypatch.setattr(voice_gestion, "check_voice_client", check_voice_client)


class TestMoveTrack:
    def test_moves_track(self, replies: Replies) -> None:
        queue = make_queue("a", "b", "c")
        asyncio.run(queue.move_track(INTERACTION, 1, 3))
        assert titles(queue) == ["b", "c", "a"]
        assert replies.messages[-1] == (
            "Move a (0:01:00) from position 1 to position 3.",
            False,
        )

    def test_moves_last_track_first(self, replies: Replies) -> None:
        queue = make_queue("a", "b", "c")
        asyncio.run(queue.move_track(INTERACTION, 3, 1))
        assert titles(queue) == ["c", "a", "b"]

    @pytest.mark.parametrize(
        ("position", "new_position"), [(0, 1), (1, 0), (4, 1), (1, 4)]
    )
    def test_rejects_out_of_range(
        self, replies: Replies, position: int, new_position: int
    ) -> None:
        queue = make_queue("a", "b", "c")
        asyncio.run(queue.move_track(INTERACTION, position, new_position))
        assert titles(queue) == ["a", "b", "c"]
        assert replies.messages[-1] == ("Numbers are incorrect!", True)

    def test_empty_queue(self, replies: Replies) -> None:
        asyncio.run(TrackQueue().move_track(INTERACTION, 1, 1))
        assert replies.messages == [("Queue is empty!", True)]


@pytest.mark.usefixtures("connected")
class TestRemoveTracks:
    def test_removes_one_track(self, replies: Replies) -> None:
        queue = make_queue("a", "b", "c")
        asyncio.run(queue.remove_tracks(INTERACTION, 2, 2))
        assert titles(queue) == ["a", "c"]
        assert replies.messages[-1] == ("Remove 1 track(s).", False)

    def test_removes_a_range(self, replies: Replies) -> None:
        queue = make_queue("a", "b", "c", "d")
        asyncio.run(queue.remove_tracks(INTERACTION, 2, 3))
        assert titles(queue) == ["a", "d"]

    def test_range_past_the_end(self, replies: Replies) -> None:
        queue = make_queue("a", "b", "c")
        asyncio.run(queue.remove_tracks(INTERACTION, 2, 10))
        assert titles(queue) == ["a"]
        assert replies.messages[-1] == ("Remove 2 track(s).", False)

    def test_without_message(self, replies: Replies) -> None:
        queue = make_queue("a", "b")
        replies.messages.clear()
        asyncio.run(queue.remove_tracks(INTERACTION, 1, 1, send_msg=False))
        assert titles(queue) == ["b"]
        assert replies.messages == []

    def test_bot_not_playing(
        self, replies: Replies, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def check_voice_client(interaction: Any) -> None:
            return None

        monkeypatch.setattr(voice_gestion, "check_voice_client", check_voice_client)
        queue = make_queue("a")
        asyncio.run(queue.remove_tracks(INTERACTION, 1, 1))
        assert titles(queue) == ["a"]
