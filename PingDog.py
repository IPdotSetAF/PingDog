import argparse
import asyncio
import time
from  os import path
import sys
from pathlib import Path
import ssl
import certifi
import aiohttp
from rich.text import Text
from textual.app import App
from textual.binding import Binding
from textual.widgets import DataTable, Header, Footer
from config import PingDogConfig
from Dialogs import QuestionDialog, InputDialog, FileDialog , OptionDialog
from PingDogCommands import PingDogCommands

ssl_context = ssl.create_default_context(cafile=certifi.where())

def read_urls_from_file(file_path):
    with open(file_path, "r") as f:
        return list(dict.fromkeys([line.strip() for line in f if line.strip()])) 

class PingDog(App):
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("i", "import", "Import URLs"),
        Binding("e", "export", "Export URLs"),
        Binding("d", "toggle_dark", "Dark"),
        Binding("t", "change_theme", "Theme"),
        Binding("a", "add_url", "Add URL"),
        Binding("delete", "delete_url", "Delete URL"),
        ]

    COMMANDS = App.COMMANDS | {PingDogCommands}

    def __init__(self, config, urls, check_interval=30):
        super().__init__()
        self.config = config
        self.urls = urls
        self.check_interval = check_interval
        self.metrics = {}

    def watch_theme(self, theme:str):
        self.config.theme = theme

    def compose(self):
        yield Header(show_clock= True)
        yield DataTable()
        yield Footer()

    async def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns(*self.columns)
        await self.check_urls()
        self.set_interval(self.check_interval, self.check_urls)
        self.theme = self.config.theme

    def action_add_url(self) -> None:
        self.push_screen(
            InputDialog(
                text="Enter URL to add:",
                title="Add URL",
                placeholder="https://example.com",
                buttons=[("Cancel", "neutral", "error"), ("Add", "positive", "primary")]
            ),
            lambda result: self.add_url(result.strip()) if result else None
        )

    def action_delete_url(self) -> None:
        table = self.query_one(DataTable)
        row =  table.cursor_row
        if row is not None:
            url = self.urls[row]
            self.push_screen(
                QuestionDialog(
                    text=f"Delete URL?\n{url}",
                    title="Confirm Deletion",
                    buttons=[("Cancel", "neutral", "primary"), ("Delete", "positive", "error")]
                ),
                lambda result: self.delete_url(row) if result else None
            )

    def action_import(self) -> None:
        def confirm(result): 
            if result :
                if len(self.urls) == 0 :
                    self.import_urls(result) 
                else :
                    self.push_screen(
                        OptionDialog(
                            text="There are URLs already in your workspace. How do you want to import new URLs?",
                            title="Import URLs Options",
                            options=[
                                ("Cancel", "cancel"),
                                ("Open (replace)", "open"),
                                ("Append", "append"),
                            ],
                        ),
                        lambda res: self.import_urls(result) if res == "open"
                        else self.import_urls(result, True) if res == "append"
                        else None
                    )

        self.push_screen(
            FileDialog(
                text="Select file to import URLs from:",
                title="Import URLs",
                select_type="file",
                check_exists=True,
                buttons=[("Cancel", "neutral", "error"), ("Import", "positive", "primary")],
                start_path=path.curdir
            ), confirm
        )
        
    def action_export(self) -> None:
        def confirm(result):
            if result:
                if Path(result).exists():
                    self.push_screen(
                        QuestionDialog(
                            text=f"File already exists, Do you want to overwrite?\n{result}",
                            title="Confirm Overwrite",
                            buttons=[("Cancel", "neutral", "primary"), ("Overwrite", "positive", "error")]
                        ),
                        lambda res: self.export_urls(result) if res else None
                    )
                else:
                    self.export_urls(result)
                    
        self.push_screen(
            FileDialog(
                text="Select file to export URLs to:",
                title="Export URLs",
                select_type="file",
                check_exists=False,
                buttons=[("Cancel", "neutral", "error"), ("Export", "positive", "primary")],
                start_path=path.curdir
            ), confirm
        )
    
    def add_url(self, url: str):
        if url and url not in self.urls:
            self.urls.append(url) # Ensure distinct URLs
            self.update_table()
            self.notify(f"Added URL: {url}")
        elif url in self.urls:
            self.notify(f"URL already exists: {url}", severity="warning")

    def delete_url(self, index: int):
        if 0 <= index < len(self.urls):
            url = self.urls.pop(index)
            self.metrics.pop(url, None)
            table = self.query_one(DataTable)
            table.remove_row(url)
            self.update_table()
            self.notify(f"Deleted URL: {url}")

    def import_urls(self, filePath, append=False):
        try:
            if append:
                self.urls = list(dict.fromkeys(self.urls + read_urls_from_file(filePath)))
            else:
                self.urls = read_urls_from_file(filePath)
            self.update_table()
            self.notify(f"Imported URLs from {filePath}")
        except Exception as e:
            self.notify(f"Failed to import: {e}", severity="error")

    def export_urls(self, filePath):
        try:
            with open(filePath, "w") as f:
                for url in self.urls:
                    f.write(url + "\n")
            self.notify(f"Exported URLs to {filePath}")
        except Exception as e:
            self.notify(f"Failed to export: {e}", severity="error")

    async def check_urls(self):
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            tasks = [self.check_url(session, url) for url in self.urls]
            results = await asyncio.gather(*tasks)
            for url, result in zip(self.urls, results):
                self.metrics[url] = result
            self.update_table()

    async def check_url(self, session, url):
        start_time = time.time()
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                return {
                    "status": response.status,
                    "response_time": time.time() - start_time,
                    "error": None,
                    "last_checked": start_time,
                }
        except Exception as e:
            return {
                "status": None,
                "response_time": None,
                "error": str(e),
                "last_checked": start_time,
            }

    columns = [
        ("URL", "url"),
        ("Status", "status"),
        ("Response Time", "response_time"),
        ("Last Checked", "last_checked")
    ]

    def update_table(self):
        table = self.query_one(DataTable)
        # If table is empty or number of rows doesn't match, reinitialize
        if len(table.rows) != len(self.urls):
            table.clear(columns=True)
            table.add_columns(*self.columns)
            for url in self.urls:
                table.add_row(Text(url), Text("N/A"), Text("N/A"), Text("N/A"), key=url)

        for url in self.urls:
            metrics = self.metrics.get(url, {})
            status = metrics.get("status")
            error = metrics.get("error")
            response_time = metrics.get("response_time")
            last_checked = metrics.get("last_checked")

            if error:
                status_text = Text(f"Error: {error}", style="red")
            else:
                if 200 <= (status or 0) < 400:
                    style = "green"
                else:
                    style = "yellow" if 400 <= (status or 0) < 500 else "red"
                status_text = Text(str(status), style=style) if status else Text("N/A")

            response_text = Text((
                f"{response_time:.2f}s" if response_time is not None else "N/A"
            ))
            last_checked_text = Text((
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_checked))
                if last_checked
                else "N/A"
            ))

            table.update_cell(url, "status", status_text, update_width=True)
            table.update_cell(url, "response_time", response_text, update_width=True)
            table.update_cell(url, "last_checked", last_checked_text, update_width=True)

def splash_screen() -> str:
    with open('art.txt', 'r', encoding='utf-8') as f:
        ascii_art = f.read()
    return ascii_art

def clear_splash_screen():
    lines = splash_screen().count('\n') or 1
    for _ in range(lines):
        sys.stdout.write('\033[F')  # move cursor up one line
        sys.stdout.write('\033[K')  # clear that line
    sys.stdout.flush()

if __name__ == "__main__":
    print(splash_screen())

    parser = argparse.ArgumentParser(
        description= "PingDog - A simple URL monitoring tool"
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to the file containing URLs (one per line)",
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="List of URLs to check (if no file is provided)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=int,
        default=5,
        help="Check interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    if args.file:
        if not Path(args.file).exists():
            print(f"Error: File '{args.file}' not found")
            exit(1)
        try:
            urls = read_urls_from_file(args.file)
        except Exception as e:
            print(f"Error reading file: {e}")
            exit(1)
    else:
        urls = list(dict.fromkeys(args.urls))

    time.sleep(1)
    clear_splash_screen()

    config_path = Path.home() / ".pingdog" / "config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    app = PingDog(PingDogConfig(str(config_path)), urls, args.interval)
    app.run()