import json
import shutil
import subprocess

from .base import BaseCheck


class SmartCheck(BaseCheck):
    NAME = "smart"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.last_health = {}
        self.smartctl_missing_reported = False

    def run(self):
        if shutil.which("smartctl") is None:
            if not self.smartctl_missing_reported:
                self.mqtt.warning(
                    f"smartctl is not installed on {self.settings.device_name}"
                )
                self.smartctl_missing_reported = True
            return

        devices = self.config.get("devices", []) or self.discover_devices()

        for device in devices:
            status = self.get_smart_status(device)

            if status is None:
                self.mqtt.warning(
                    f"SMART check failed on {self.settings.device_name}: {device}"
                )
                continue

            device_id = device.strip("/").replace("/", "_")
            healthy = status["healthy"]
            temperature = status.get("temperature")
            previous = self.last_health.get(device)

            if healthy is not None:
                self.mqtt.publish(
                    f"smart/{device_id}/healthy",
                    1 if healthy else 0,
                )

            if temperature is not None:
                self.mqtt.publish(
                    f"smart/{device_id}/temperature",
                    temperature,
                )

            if healthy is False and previous is not False:
                self.mqtt.warning(
                    f"SMART health FAILED on "
                    f"{self.settings.device_name}: {device}"
                )
            elif healthy is True and previous is False:
                self.mqtt.info(
                    f"SMART health recovered on "
                    f"{self.settings.device_name}: {device}"
                )

            if healthy is not None:
                self.last_health[device] = healthy

    @staticmethod
    def discover_devices():
        try:
            result = subprocess.run(
                ["smartctl", "--scan-open"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            devices = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                devices.append(line.split()[0])

            return devices
        except Exception:
            return []

    @staticmethod
    def get_smart_status(device):
        try:
            result = subprocess.run(
                ["smartctl", "-a", "-j", device],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if not result.stdout.strip():
                return None

            data = json.loads(result.stdout)

            healthy = data.get("smart_status", {}).get("passed")

            temperature = None
            temp_obj = data.get("temperature")
            if isinstance(temp_obj, dict):
                temperature = temp_obj.get("current")

            if temperature is None:
                nvme = data.get("nvme_smart_health_information_log", {})
                temperature = nvme.get("temperature")

            return {
                "healthy": healthy,
                "temperature": temperature,
            }
        except (json.JSONDecodeError, OSError, subprocess.SubprocessError):
            return None
