import time


class BaseCheck:
    NAME = "base"

    def __init__(self, settings, mqtt):
        self.settings = settings
        self.mqtt = mqtt
        self.config = settings.check_config(self.NAME)
        self.interval = settings.check_interval(self.NAME)
        self.last_run = None

    def should_run(self) -> bool:
        if self.last_run is None:
            return True
        return time.monotonic() - self.last_run >= self.interval

    def run_if_needed(self):
        if not self.should_run():
            return

        try:
            self.run()
        finally:
            self.last_run = time.monotonic()

    def run(self):
        raise NotImplementedError
