from pathlib import Path

from .base import BaseCheck


class CpuTempCheck(BaseCheck):
    NAME = "cpu_temp"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.path_warning_sent = False

    def run(self):
        configured_path = self.config.get("path")
        paths = []

        if configured_path:
            paths.append(Path(configured_path))
        else:
            paths.extend(sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")))

        path = next((item for item in paths if item.exists()), None)

        if path is None:
            if not self.path_warning_sent:
                self.mqtt.warning(
                    f"CPU temperature sensor not found on {self.settings.device_name}"
                )
                self.path_warning_sent = True
            return

        try:
            raw = float(path.read_text().strip())
            temp = raw / 1000.0 if raw > 1000 else raw
        except Exception as exc:
            self.mqtt.warning(
                f"CPU temperature read failed on {self.settings.device_name}: {exc}"
            )
            return

        self.path_warning_sent = False
        self.mqtt.publish("cpu_temp", f"{temp:.2f}")

        warning_temp = float(self.config.get("warning_temp", 65))
        if temp >= warning_temp:
            self.mqtt.warning(
                f"High CPU temperature on {self.settings.device_name}: {temp:.2f} C"
            )
