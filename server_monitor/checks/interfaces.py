from pathlib import Path

from .base import BaseCheck


class InterfacesCheck(BaseCheck):
    NAME = "interfaces"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.states = {}

    def run(self):
        for interface in self.config.get("names", []):
            state = self.get_state(interface)
            previous = self.states.get(interface)

            if previous is None:
                if state == "missing":
                    self.mqtt.warning(
                        f"Interface {interface} is missing on "
                        f"{self.settings.device_name}"
                    )
            elif previous != state:
                self.mqtt.warning(
                    f"Interface {interface} changed state on "
                    f"{self.settings.device_name}: {previous} -> {state}"
                )

            self.states[interface] = state

    @staticmethod
    def get_state(interface: str) -> str:
        base = Path(f"/sys/class/net/{interface}")

        if not base.exists():
            return "missing"

        try:
            return (base / "operstate").read_text().strip()
        except Exception:
            return "unknown"
