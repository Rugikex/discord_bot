from typing import Any

SKIP_TIMER: float = 10.0
ADD_QUEUE_TIMER: float = 5.0
SAVE_SETTINGS_TIMER: float = 300.0

SONG_REACTIONS: list[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
QUEUE_REACTIONS: list[str] = ["⬆️", "⬇️"]

MSG_BLACKLIST: str = "Sorry, you can't use this bot."

DEFAULT_SETTINGS: dict[str, Any] = {
    "default_platform": "youtube",
    "default_tracks": {"link": None, "platform": None},
}
