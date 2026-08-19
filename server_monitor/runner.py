import time

from .checks import AVAILABLE_CHECKS


class MonitorRunner:
    def __init__(self, settings, mqtt):
        self.settings = settings
        self.mqtt = mqtt
        self.checks = []

    def setup_checks(self):
        for check_class in AVAILABLE_CHECKS:
            if self.settings.check_enabled(check_class.NAME):
                self.checks.append(check_class(self.settings, self.mqtt))

    def run_forever(self):
        self.setup_checks()

        names = ", ".join(check.NAME for check in self.checks) or "none"
        print(f"Enabled checks: {names}")
        self.mqtt.info(f"{self.settings.device_name} monitor started")

        loop_interval = float(self.settings.raw.get("loop_interval", 1))

        try:
            while True:
                for check in self.checks:
                    try:
                        check.run_if_needed()
                    except Exception as exc:
                        print(f"Check {check.NAME} failed: {exc}")

                time.sleep(loop_interval)

        except KeyboardInterrupt:
            print("Stopping server-monitor")
