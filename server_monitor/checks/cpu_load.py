import psutil

from .base import BaseCheck


class CpuLoadCheck(BaseCheck):
    NAME = "cpu_load"

    def run(self):
        load = psutil.cpu_percent(interval=None)
        self.mqtt.publish("cpu_load", f"{load:.2f}")
