from textual.app import App, Screen
from textual.command import Provider, Hit, Hits
from functools import partial

class PingDogCommands(Provider):
    def __init__(self, app: App, screen: Screen) -> None:
        super().__init__(app)
        self.commands = [
            {
                "name": "Import URLs",
                "callback": self.app.action_import,
                "help": "Import URLs from a file",
                "discover": True,
            },
            {
                "name": "Export URLs",
                "callback": self.app.action_export,
                "help": "Export URLs to a file",
                "discover": True,
            },
        ]

    async def discover(self) -> Hits:
        for cmd in self.commands:
            if cmd.get("discover", False):
                yield Hit(
                    100,
                    cmd["name"],
                    partial(cmd["callback"]),
                    help=cmd.get("help", ""),
                )
    
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for cmd in self.commands:
            score = matcher.match(cmd["name"])
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(cmd["name"]),
                    partial(cmd["callback"]),
                    help=cmd.get("help", ""),
                )