from dataclasses import dataclass
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass
class Settings:
    raw: dict

    @property
    def device_name(self) -> str:
        return self.raw.get("device_name", "Unknown")

    @property
    def topic_prefix(self) -> str:
        return self.raw.get("topic_prefix", "").strip("/")

    @property
    def mqtt(self) -> dict:
        return self.raw["mqtt"]

    @property
    def topics(self) -> dict:
        return self.raw.get("mqtt", {}).get("topics", {})

    def check_enabled(self, name: str) -> bool:
        return bool(
            self.raw.get("checks", {}).get(name, {}).get("enabled", False)
        )

    def check_interval(self, name: str) -> float:
        return float(
            self.raw.get("checks", {}).get(name, {}).get("interval", 10)
        )

    def check_config(self, name: str) -> dict:
        return self.raw.get("checks", {}).get(name, {})


def load_settings(path: str | Path) -> Settings:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("rb") as file:
        raw = tomllib.load(file)

    if "mqtt" not in raw:
        raise ValueError("Config section [mqtt] is required")

    if "broker" not in raw["mqtt"]:
        raise ValueError("mqtt.broker is required")

    return Settings(raw)
