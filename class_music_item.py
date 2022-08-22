class MusicItem:
    def __init__(self, platform, title, duration, link):
        self.platform = platform
        self.title = title
        self.duration = duration
        self.link = link

    def __str__(self):
        return f"{self.title} ({self.duration})"
