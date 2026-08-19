import subprocess

from .base import BaseCheck


class ServicesCheck(BaseCheck):
    NAME = "services"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.states = {}

    def run(self):
        for service in self.config.get("names", []):
            status = self.get_status(service)
            previous = self.states.get(service)

            if previous is None:
                if status != "active":
                    self.mqtt.warning(
                        f"Service {service} is {status} on "
                        f"{self.settings.device_name}"
                    )
            elif previous == "active" and status != "active":
                self.mqtt.warning(
                    f"Service {service} failed on "
                    f"{self.settings.device_name}: status={status}"
                )
            elif previous != "active" and status == "active":
                self.mqtt.info(
                    f"Service {service} recovered on {self.settings.device_name}"
                )

            self.states[service] = status

    @staticmethod
    def get_status(service: str) -> str:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"
