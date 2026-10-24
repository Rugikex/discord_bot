from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any

import pytest

import classes.music_source.local as local
from classes.music_source.youtube import YoutubeSource
from classes.track import Track

from .conftest import make_track


class TestYoutubeIsLink:
    @pytest.mark.parametrize(
        "query",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PL123",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RD123",
        ],
    )
    def test_links(self, query: str) -> None:
        assert YoutubeSource().is_link(query)

    @pytest.mark.parametrize(
        "query", ["never gonna give you up", "https://example.com/video"]
    )
    def test_searches(self, query: str) -> None:
        assert not YoutubeSource().is_link(query)


class TestYoutubeLoad:
    """yt-dlp is replaced: no network access."""

    @pytest.fixture
    def source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[YoutubeSource, list[str]]:
        source = YoutubeSource()
        calls: list[str] = []

        async def single_link(link: str, requester: Any) -> list[Track]:
            calls.append(f"single {link}")
            return [make_track("video")]

        async def playlist_link(link: str, requester: Any) -> list[Track]:
            calls.append(f"playlist {link}")
            return []  # Unreadable playlist, like a YouTube mix

        monkeypatch.setattr(source, "_single_link", single_link)
        monkeypatch.setattr(source, "_playlist_link", playlist_link)
        return source, calls

    def test_video(self, source: tuple[YoutubeSource, list[str]]) -> None:
        youtube, calls = source
        tracks = asyncio.run(youtube.load("https://youtu.be/abc", None))  # type: ignore[arg-type]
        assert [track.title for track in tracks] == ["video"]
        assert calls == ["single https://youtu.be/abc"]

    def test_unreadable_playlist_loads_the_video(
        self, source: tuple[YoutubeSource, list[str]]
    ) -> None:
        youtube, calls = source
        tracks = asyncio.run(
            youtube.load("https://www.youtube.com/watch?v=abc&list=RD1", None)  # type: ignore[arg-type]
        )
        assert [track.title for track in tracks] == ["video"]
        assert calls[-1] == "single https://youtu.be/abc"


class TestLocalSearch:
    @pytest.fixture(autouse=True)
    def fake_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        names = [
            "Daft Punk - Around the World",
            "Queen - Bohemian Rhapsody",
            "Daft Punk - One More Time",
            "Random noise",
        ]
        monkeypatch.setattr(
            local, "list_local_files", lambda: [Path(f"music/{n}.mp3") for n in names]
        )
        # No audio file to decode: one track per path
        monkeypatch.setattr(
            local,
            "load_local_tracks",
            lambda paths, requester: [make_track(p.stem) for p in paths],
        )

    def test_best_matches(self) -> None:
        tracks = asyncio.run(local.LocalSource().search("daft punk", None))  # type: ignore[arg-type]
        assert {track.title for track in tracks} == {
            "Daft Punk - Around the World",
            "Daft Punk - One More Time",
        }

    def test_no_match(self) -> None:
        assert asyncio.run(local.LocalSource().search("zzzzqqqq", None)) == []  # type: ignore[arg-type]

    def test_is_never_a_link(self) -> None:
        assert not local.LocalSource().is_link("music/song.mp3")
