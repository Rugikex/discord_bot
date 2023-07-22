import datetime


class MusicItem:
    def __init__(self, title: str, duration: datetime.timedelta | None, link: str):
        self.title = title
        self.duration = duration if duration is not None else "???"
        self.link = link

    def __str__(self) -> str:
        return f"{self.title} ({self.duration})"
