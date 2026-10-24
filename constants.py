from pathlib import Path
from typing import Any

BASE_DIR: Path = Path(__file__).resolve().parent

SKIP_TIMER: float = 10.0
ADD_QUEUE_TIMER: float = 5.0

SONG_REACTIONS: list[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
MAX_SEARCH_RESULTS: int = len(SONG_REACTIONS)
# Seconds before the buttons of a search expire (its message is then deleted)
SEARCH_TIMEOUT: float = 180.0
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
    # Seconds before public answers to commands are deleted (0 to keep them)
    "delete_replies_after": 60,
}
# Interactions expire after 15 minutes: a later deletion would fail
MAX_DELETE_REPLIES_AFTER: int = 600
