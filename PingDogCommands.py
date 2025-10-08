from textual.app import App, Screen
from textual.command import Provider, Hit, Hits
from functools import partial

class PingDogCommands(Provider):
    def __init__(self, app: App, screen: Screen) -> None:
        super().__init__(app)
        self.commands = [
            ("Import URLs", self.app.action_import, "Import URLs from a file", True),
            ("Export URLs", self.app.action_export, "Export URLs to a file", True),
        ]

    async def discover(self) -> Hits:
        for cmd, callback, help, discover in self.commands:
            if discover:
                yield Hit(
                    100,
                    cmd,
                    partial(callback),
                    help=help,
                )
    
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for cmd, callback, help, discover in self.commands:
            score = matcher.match(cmd)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(cmd),
                    partial(callback),
                    help=help,
                )