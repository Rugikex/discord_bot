from typing import Any

SKIP_TIMER: float = 10.0
ADD_QUEUE_TIMER: float = 5.0

SONG_REACTIONS: list[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
QUEUE_REACTIONS: list[str] = ["⬆️", "⬇️"]

MSG_BLACKLIST: str = "Sorry, you can't use this bot."

DEFAULT_SETTINGS: dict[str, Any] = {
    "default_platform": "youtube",
    "default_tracks": {"link": None, "platform": None},
    # Played when the bot joins a voice channel (null to disable)
    "welcome_track": {
        "link": "https://www.youtube.com/watch?v=hSU0Z3_466s",
        "platform": "youtube",
    },
}
