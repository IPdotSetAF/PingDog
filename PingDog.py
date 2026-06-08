import argparse
import asyncio
import re
from datetime import timedelta
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
from textual.widgets import DataTable, Header, Footer, Label
from textual.containers import Horizontal, Vertical
from config import PingDogConfig
from Dialogs import QuestionDialog, InputDialog, FileDialog , OptionDialog
from PingDogCommands import PingDogCommands

ssl_context = ssl.create_default_context(cafile=certifi.where())

def read_urls_from_file(file_path):
    with open(file_path, "r") as f:
        return list(dict.fromkeys([line.strip() for line in f if line.strip()])) 

class PingDog(App):
    
    DEFAULT_CSS = """
    #info {
        background: $panel;
        color: $foreground;
        height: 1;
        align-horizontal: center;
    }
    #info *{
        padding: 0 1;
    }
    """
    
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
        self.ip_cache = {}
        
    def watch_theme(self, theme:str):
        self.config.theme = theme

    def compose(self):
        yield Header(show_clock= True)
        with Vertical():
            with Horizontal(id= 'info'):
                yield Label("Last Checked:")
                yield Label("N/A", id = "last_checked")
                yield Label("-") 
                yield Label(f"Updates every {timedelta(seconds=self.check_interval)}")
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
            self.ip_cache.pop(url, None)
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
            self.update_info(time.time())
            self.update_table()
            
    def cache_ip(self, url, ip=None) -> str:
        now = time.time()
        if ip:
            self.ip_cache[url] = {"cache_time": now, "cache_ip": ip}
            return ip
        else:
            cached_ip = self.ip_cache.get(url)
            if not cached_ip:
                return None
            if cached_ip["cache_time"] + self.config.ip_cache_seconds >= now:
                return cached_ip["cache_ip"]
            else:
                self.ip_cache.pop(url, None)
                return None
            
    async def check_url(self, session, url):
        start_time = time.time()
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                ip_port = response.connection.transport.get_extra_info('peername') if response.connection else None
                return {
                    "status": response.status,
                    "response_time": time.time() - start_time,
                    "error": None,
                    "ip": self.cache_ip(url, f"{ip_port[0]}:{ip_port[1]}" if ip_port else None)
                }
        except Exception as e:
            return {
                "status": None,
                "response_time": None,
                "error": str(e),
                "ip": self.cache_ip(url, None)
            }

    columns = [
        ("Protocol", "protocol"),
        ("URL", "url"),
        ("Status", "status"),
        ("Response Time", "response_time"),
        ("IP", "ip"),
        ("Detail", "detail"),
    ]

    response_time_colors = ["green", "bright_yellow", "yellow", "red"]
    response_time_ranges = {
        "http": [100, 300, 700],
    }

    def get_range_index(self, ranges, value):
        for i, v in enumerate(ranges):
            if value <= v:
                return i
        return len(ranges)
        
    def update_table(self):
        table = self.query_one(DataTable)
        
        if len(table.rows) != len(self.urls):
            table.clear(columns=True)
            table.add_columns(*self.columns)
            for url in self.urls:
                if url.startswith('https://'):
                    table.add_row(Text("\U0001F512HTTPS"), Text(url), Text("N/A"), Text("N/A"), Text("N/A"), Text(""), key=url)
                else:
                    table.add_row(Text("\U0001F513HTTP"), Text(url), Text("N/A"), Text("N/A"), Text("N/A"), Text(""), key=url)

        for url in self.urls:
            metrics = self.metrics.get(url, {})
            status = metrics.get("status")
            error = metrics.get("error")
            response_time = metrics.get("response_time")
            ip = metrics.get("ip")
            
            row_style = None if (status and status < 500) else "red"
            
            url_text = Text(url, style = row_style)
            
            if 200 <= (status or 0) < 400:
                style = "green"
            else:
                style = "yellow" if 400 <= (status or 0) < 500 else "red"
            status_text = Text(str(status), style=style) if status else Text("N/A", style=style)

            detail_text = Text(f"Error: {error}" if error else "", style = style)
             
            if response_time is not None:
                response_time = response_time * 1000
                style =  self.response_time_colors[self.get_range_index(self.response_time_ranges["http"], response_time)]
                response_text = Text((f"{response_time:.0f}ms" if response_time>= 10 else f"{response_time:.2f}ms") if response_time is not None else "N/A", style = style)
            else:
                response_text = Text("N/A", style = "red")
                
            if ip:
                ip_text = Text(ip, style = row_style)
            else:
                ip_text = Text("N/A", style = row_style or "yellow")
                
            table.update_cell(url, "url", url_text)
            table.update_cell(url, "status", status_text, update_width=True)
            table.update_cell(url, "response_time", response_text, update_width=True)
            table.update_cell(url, "ip", ip_text, update_width=True)
            table.update_cell(url, "detail", detail_text, update_width=True)

    def update_info(self, last_checked):
        self.query_one("#last_checked", Label).update(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_checked)) if last_checked else "N/A")
        
def splash_screen() -> str:
    RED = '\033[91m'
    RESET = '\033[0m'
    splash = r'''
     _/\/\/\/\/\____/\/\________________________________/\/\/\/\/\___________________________
    _/\/\____/\/\__________/\/\/\/\______/\/\/\/\______/\/\____/\/\____/\/\/\______/\/\/\/\_ 
   _/\/\/\/\/\____/\/\____/\/\__/\/\__/\/\__/\/\______/\/\____/\/\__/\/\__/\/\__/\/\__/\/\_  
  _/\/\__________/\/\____/\/\__/\/\____/\/\/\/\______/\/\____/\/\__/\/\__/\/\____/\/\/\/\_   
 _/\/\__________/\/\/\__/\/\__/\/\________/\/\______/\/\/\/\/\______/\/\/\__________/\/\_    
___________________________________/\/\/\/\__________________________________/\/\/\/\___     
'''
    return re.sub(r"((/\\)+)", rf'{RED}\1{RESET}', splash)

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
    parser.version = "PingDog v1.1.0"
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="Show PingDog version",
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