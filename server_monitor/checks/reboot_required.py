from pathlib import Path

from .base import BaseCheck


class RebootRequiredCheck(BaseCheck):
    NAME = "reboot_required"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.last_state = False

    def run(self):
        path = Path(self.config.get("file", "/var/run/reboot-required"))
        current = path.exists()

        if current and not self.last_state:
            self.mqtt.info(f"Reboot is required for {self.settings.device_name}")

        if not current and self.last_state:
            self.mqtt.info(
                f"Reboot-required flag cleared on {self.settings.device_name}"
            )

        self.last_state = current
