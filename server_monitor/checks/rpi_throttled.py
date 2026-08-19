import shutil
import subprocess

from .base import BaseCheck


class RpiThrottledCheck(BaseCheck):
    NAME = "rpi_throttled"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.last_value = 0
        self.unavailable_reported = False

    def run(self):
        if shutil.which("vcgencmd") is None:
            if not self.unavailable_reported:
                print("rpi_throttled: vcgencmd not installed; check skipped")
                self.unavailable_reported = True
            return

        status = self.get_status()
        if status is None:
            return

        current_value = status["value"]
        if current_value == self.last_value:
            return

        if status["under_voltage_now"]:
            self.mqtt.warning(
                f"Raspberry Pi under-voltage NOW on "
                f"{self.settings.device_name}: {status['raw']}"
            )
        elif status["under_voltage_ever"] and not (self.last_value & 0x10000):
            self.mqtt.warning(
                f"Raspberry Pi under-voltage was detected earlier on "
                f"{self.settings.device_name}: {status['raw']}"
            )

        if status["throttled_now"]:
            self.mqtt.warning(
                f"Raspberry Pi is throttled NOW on "
                f"{self.settings.device_name}: {status['raw']}"
            )
        elif status["throttled_ever"] and not (self.last_value & 0x40000):
            self.mqtt.warning(
                f"Raspberry Pi throttling was detected earlier on "
                f"{self.settings.device_name}: {status['raw']}"
            )

        self.last_value = current_value

    @staticmethod
    def get_status():
        try:
            result = subprocess.run(
                ["vcgencmd", "get_throttled"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            output = result.stdout.strip()

            if not output.startswith("throttled="):
                return None

            value = int(output.split("=")[1], 16)
            return {
                "raw": output,
                "value": value,
                "under_voltage_now": bool(value & 0x1),
                "frequency_capped_now": bool(value & 0x2),
                "throttled_now": bool(value & 0x4),
                "soft_temp_limit_now": bool(value & 0x8),
                "under_voltage_ever": bool(value & 0x10000),
                "frequency_capped_ever": bool(value & 0x20000),
                "throttled_ever": bool(value & 0x40000),
                "soft_temp_limit_ever": bool(value & 0x80000),
            }
        except Exception:
            return None
