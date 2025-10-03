import yaml
import os

class Config:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path
        self.data = {}
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

    def __repr__(self):
        return f"Config({self.yaml_path}): {self.data}"


class PingDogConfig(Config):
    DEFAULTS = {
        "theme": "textual-dark",    # default theme
        "timeout": 2,               # seconds
        "log_file": "pingdog.log",  # default log file
    }

    def __init__(self, yaml_path):
        super().__init__(yaml_path)
        # Set missing defaults
        changed = False
        for key, value in self.DEFAULTS.items():
            if key not in self.data:
                self.data[key] = value
                changed = True
        if changed:
            self.save()

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
