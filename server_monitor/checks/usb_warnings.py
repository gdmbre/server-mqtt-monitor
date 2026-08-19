import subprocess
from datetime import datetime

from .base import BaseCheck


class UsbWarningsCheck(BaseCheck):
    NAME = "usb_warnings"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.last_check_time = None
        self.seen_warnings = set()

    def run(self):
        for line in self.get_recent_warnings():
            self.mqtt.warning(
                f"USB/kernel warning on {self.settings.device_name}: {line}"
            )

    def get_recent_warnings(self):
        if self.last_check_time is None:
            since = "1 minute ago"
        else:
            since = self.last_check_time

        self.last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            result = subprocess.run(
                [
                    "journalctl",
                    "-k",
                    "--since",
                    since,
                    "--no-pager",
                    "-o",
                    "short-iso",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            keywords = [
                item.lower()
                for item in self.config.get("keywords", [])
                if item.strip()
            ]

            warnings = []
            for line in result.stdout.splitlines():
                low = line.lower()

                if keywords and any(keyword in low for keyword in keywords):
                    line = line.strip()
                    if line not in self.seen_warnings:
                        self.seen_warnings.add(line)
                        warnings.append(line)

            if len(self.seen_warnings) > 500:
                self.seen_warnings.clear()

            return warnings[-10:]
        except Exception:
            return []
