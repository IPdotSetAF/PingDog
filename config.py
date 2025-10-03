import yaml
import os
import argparse
from pathlib import Path

class Config:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.data = {}
        # self.fields = {}
        if os.path.exists(yaml_path):
            self.load()
        else:
            self.data = {}
            self.save()

    def load(self):
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f) or {}

    def save(self):
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.data, f, default_flow_style=False, allow_unicode=True)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def load_args(self, argv=None):
        parser = argparse.ArgumentParser(add_help=True)
        for field in self.fields.keys():
            if self.fields[field].expose:
                parser.add_argument(
                    self.fields[field].short,
                    f'--{field}',
                    type=self.fields[field].type,
                    default=self.fields[field].default,
                    help=self.fields[field].help
                )

        if argv:
            args = vars(parser.parse_args(argv))
        else: 
            args = vars(parser.parse_args())
        for arg in args.keys():
            self.data[arg] = args[arg]

    def __repr__(self):
        return f"Config({self.yaml_path}): {self.data}"

class ConfigField:
    def __init__(self, short, expose, default, type, help):
        self.short = short
        self.expose = expose
        self.default = default
        self.type = type
        self.help = help

    def __repr__(self):
        return f"ConfigField({self.short}, {self.expose}, {self.default}, {self.type}, {self.help})\n"

class PingDogConfig(Config):
    fields = {
        "theme": ConfigField( None, False, "textual-dark", str, "Theme for the UI (e.g. textual-dark, monokai, etc.)"),
        "timeout": ConfigField( "-t", True, 2, int, "Timeout in seconds for URL check"),
        "interval": ConfigField( "-i", True, 5, int, "Seconds between checks"),
        "file": ConfigField( "-f", True, None, str, "Path to file containing URLs to monitor (one per line)"),
        "log": ConfigField( "-l", True, "pingdog.log", str, "Path to the log file"),
    }

    def __init__(self, yaml_path):
        super().__init__(yaml_path)
        # Set missing defaults
        changed = False
        for key, value in self.fields.items():
            if key not in self.data:
                self.data[key] = value.default
                changed = True
        if changed:
            self.save()

    # -----------------
    # Argument handling
    # -----------------
    def _load_args_and_merge(self, expose_fields=None, argv=None):
       
        parser = argparse.ArgumentParser(add_help=True)

        # Always include file option for URL loading
        parser.add_argument(
            "-f", "--file", type=str, help="Path to file containing URLs (one per line)")
        # Expose known config fields as optional args by default
        keys_to_expose = set(self.data.keys()) if expose_fields is None else set(expose_fields)

        for key in sorted(keys_to_expose):
            if key == "urls":
                # Allow passing urls via --urls url1 url2 ...
                parser.add_argument(f"--{key}", nargs="*", help="List of URLs to monitor")
                continue

            current_value = self.data.get(key)
            arg_name = f"--{key.replace('_', '-')}"

            # Infer type for argparse
            arg_kwargs = {}
            if isinstance(current_value, bool):
                # For booleans, accept true/false strings
                def str2bool(v):
                    if isinstance(v, bool):
                        return v
                    s = str(v).strip().lower()
                    if s in {"1", "true", "t", "yes", "y", "on"}:
                        return True
                    if s in {"0", "false", "f", "no", "n", "off"}:
                        return False
                    raise argparse.ArgumentTypeError("expected a boolean")
                arg_kwargs["type"] = str2bool
            elif isinstance(current_value, int):
                arg_kwargs["type"] = int
            elif isinstance(current_value, float):
                arg_kwargs["type"] = float
            else:
                arg_kwargs["type"] = str

            parser.add_argument(arg_name, **arg_kwargs)

        # Parse known args; collect leftovers as URLs
        args, extras = parser.parse_known_args(argv)

        # Merge scalar options back into config if provided
        for key in keys_to_expose:
            if key == "urls":
                continue
            arg_attr = key.replace('-', '_')
            if hasattr(args, arg_attr):
                value = getattr(args, arg_attr)
                if value is not None:
                    self.data[key] = value

        # Collect URLs from: existing config, --urls option, file, and extra positionals
        urls_from_config = list(self.data.get("urls", []) or [])
        urls_from_flag = getattr(args, "urls", None) or []
        urls_from_file = []
        if getattr(args, "file", None):
            file_path = Path(getattr(args, "file"))
            if file_path.exists():
                try:
                    with file_path.open("r", encoding="utf-8") as f:
                        urls_from_file = [line.strip() for line in f if line.strip()]
                except Exception:
                    # If file can't be read, ignore silently here; app may warn later
                    urls_from_file = []

        urls_from_extras = [s for s in extras if not s.startswith("-")]

        combined_urls = self._unique_preserve_order(
            urls_from_config + urls_from_flag + urls_from_file + urls_from_extras
        )
        self.data["urls"] = combined_urls

        # Persist updates
        self.save()

    @staticmethod
    def _unique_preserve_order(items):
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @property
    def theme(self):
        return self.data.get("theme", self.DEFAULTS["theme"])

    @theme.setter
    def theme(self, value):
        self.data["theme"] = value
        self.save()

    @property
    def timeout(self):
        return self.data.get("timeout", self.DEFAULTS["timeout"])

    @timeout.setter
    def timeout(self, value):
        self.data["timeout"] = value
        self.save()

    @property
    def log_file(self):
        return self.data.get("log_file", self.DEFAULTS["log_file"])

    @log_file.setter
    def log_file(self, value):
        self.data["log_file"] = value
        self.save()

    @property
    def interval(self):
        return self.data.get("interval", self.DEFAULTS["interval"])

    @interval.setter
    def interval(self, value):
        self.data["interval"] = value
        self.save()

    @property
    def urls(self):
        return list(self.data.get("urls", []) or [])

    @urls.setter
    def urls(self, value):
        self.data["urls"] = list(value or [])
        self.save()
