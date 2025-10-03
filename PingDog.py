import argparse
import asyncio
import time
from pathlib import Path
import ssl
import certifi
import aiohttp
from rich.text import Text
from textual.app import App
from textual.widgets import DataTable, Header
from config import PingDogConfig

ssl_context = ssl.create_default_context(cafile=certifi.where())


def read_urls_from_file(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]


class PingDog(App):
    BINDINGS = [("q", "quit", "Quit")]
    title = ""

    def __init__(self, config, urls, check_interval=30):
        super().__init__()
        self.config = config
        self.urls = urls
        self.check_interval = check_interval
        self.metrics = {}

        self.theme = self.config.theme

    def watch_theme(self, theme:str):
        self.config.theme = theme
        # self.theme.set_theme(theme)

    def compose(self):
        yield Header()
        yield DataTable()

    async def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("URL", "Status", "Response Time", "Last Checked")
        await self.check_urls()
        self.set_interval(self.check_interval, self.check_urls)

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
                url, timeout=aiohttp.ClientTimeout(total=10)
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

    def update_table(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("URL", "Status", "Response Time", "Last Checked")

        for url in self.urls:
            metrics = self.metrics.get(url, {})
            status = metrics.get("status")
            error = metrics.get("error")
            response_time = metrics.get("response_time")
            last_checked = metrics.get("last_checked")

            # Create styled status text
            if error:
                status_text = Text(f"Error: {error}", style="red")
            else:
                if 200 <= (status or 0) < 400:
                    style = "green"
                else:
                    style = "yellow" if 400 <= (status or 0) < 500 else "red"
                status_text = Text(str(status), style=style) if status else Text("N/A")

            # Format response time
            response_time_str = (
                f"{response_time:.2f}s" if response_time is not None else "N/A"
            )
            response_text = Text(response_time_str)

            # Format last checked time
            last_checked_str = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_checked))
                if last_checked
                else "N/A"
            )
            last_checked_text = Text(last_checked_str)

            table.add_row(
                Text(url),
                status_text,
                response_text,
                last_checked_text,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitor website availability from a file or a list of URLs"
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
        default=30,
        help="Check interval in seconds (default: 30)",
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
        urls = args.urls

    if not urls:
        print("No valid URLs provided (use -f FILE or provide URLs as arguments)")
        exit(1)

    app = PingDog(PingDogConfig("config.yml"), urls, args.interval)
    app.run()