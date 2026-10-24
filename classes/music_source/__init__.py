from .base import MusicSource
from .local import LocalSource
from .youtube import YoutubeSource

# Key = Track.origin and value of the "platform" choices / settings
MUSIC_SOURCES: dict[str, MusicSource] = {
    "local": LocalSource(),
    "youtube": YoutubeSource(),
}

__all__ = [
    "MUSIC_SOURCES",
    "MusicSource",
    "LocalSource",
    "YoutubeSource",
]
