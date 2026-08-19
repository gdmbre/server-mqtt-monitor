import subprocess

from .base import BaseCheck


class LastLoginCheck(BaseCheck):
    NAME = "last_login"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.last_login_line = self.get_last_login_line()

    def run(self):
        current = self.get_last_login_line()

        if current and self.last_login_line and current != self.last_login_line:
            self.mqtt.warning(
                f"New system login detected on "
                f"{self.settings.device_name}: {current}"
            )

        if current:
            self.last_login_line = current

    @staticmethod
    def get_last_login_line():
        try:
            result = subprocess.run(
                ["last", "-n", "1"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            lines = result.stdout.splitlines()
            if not lines:
                return None

            line = lines[0].strip()
            if line.startswith("wtmp begins"):
                return None

            return line
        except Exception:
            return None
