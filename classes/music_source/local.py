from __future__ import annotations
import asyncio
from datetime import timedelta
from mutagen import File, MutagenError
from pathlib import Path
from typing import TYPE_CHECKING, override

from discord import Color
from thefuzz import fuzz

from .base import FFmpegOptions, MusicSource
from classes.track import Track
from constants import BASE_DIR, MAX_SEARCH_RESULTS

if TYPE_CHECKING:
    import discord


MUSIC_FOLDER: Path = BASE_DIR / "music"
AUDIO_EXTENSIONS: tuple[str, ...] = (".mp3", ".wav", ".flac")
# Minimal fuzzy score (0-100) between the query and a file name
MIN_SEARCH_SCORE: int = 50


def list_local_files() -> list[Path]:
    if not MUSIC_FOLDER.is_dir():
        return []
    return [
        path
        for path in MUSIC_FOLDER.iterdir()
        if path.suffix.lower() in AUDIO_EXTENSIONS
    ]


def load_local_track(
    path: str | Path, requester: discord.User | discord.Member
) -> Track | None:
    """Blocking (reads the file): run it in an executor."""
    # A relative path (e.g. "music/intro.mp3" in the settings) starts from BASE_DIR
    path = BASE_DIR / path
    try:
        audio = File(path)
    except (MutagenError, OSError):
        return None
    if audio is None or audio.info is None:
        return None

    return Track(
        path.stem,
        timedelta(seconds=int(audio.info.length)),
        str(path),
        "local",
        requester,
    )


def load_local_tracks(
    paths: list[Path], requester: discord.User | discord.Member
) -> list[Track]:
    """Blocking (reads files): run it in an executor."""
    tracks: list[Track] = []
    for path in paths:
        track: Track | None = load_local_track(path, requester)
        if track is not None:
            tracks.append(track)
    return tracks


class LocalSource(MusicSource):
    color: Color = Color.from_str("#1F3F68")
    logo: str = "server-logo.png"

    @override
    def get_url(self, track: Track) -> str | None:
        return None

    @override
    async def get_track(
        self, link: str, requester: discord.User | discord.Member
    ) -> Track | None:
        return await asyncio.to_thread(load_local_track, link, requester)

    @override
    async def search(
        self, query: str, requester: discord.User | discord.Member
    ) -> list[Track]:
        scores: list[tuple[int, Path]] = [
            (fuzz.WRatio(query, path.stem), path) for path in list_local_files()
        ]
        scores.sort(key=lambda score_path: score_path[0], reverse=True)
        best_paths: list[Path] = [
            path for score, path in scores if score >= MIN_SEARCH_SCORE
        ][:MAX_SEARCH_RESULTS]

        return await asyncio.to_thread(load_local_tracks, best_paths, requester)

    @override
    async def get_stream_url(self, track: Track) -> tuple[str | None, FFmpegOptions]:
        return track.link, {"options": "-vn -loglevel quiet"}
