import time
import psutil

from .base import BaseCheck


class NetworkSpeedCheck(BaseCheck):
    NAME = "network_speed"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.previous = {}

    def run(self):
        interfaces = self.config.get("interfaces")
        if not interfaces:
            single = self.config.get("interface")
            interfaces = [single] if single else []

        now = time.monotonic()
        counters = psutil.net_io_counters(pernic=True)

        for interface in interfaces:
            if interface not in counters:
                self.mqtt.warning(
                    f"Network interface {interface} not found on "
                    f"{self.settings.device_name}"
                )
                continue

            current = counters[interface]
            previous = self.previous.get(interface)
            self.previous[interface] = (
                now,
                current.bytes_sent,
                current.bytes_recv,
            )

            if previous is None:
                continue

            prev_time, prev_sent, prev_recv = previous
            elapsed = now - prev_time

            if elapsed <= 0:
                continue

            byte_delta = (
                current.bytes_sent - prev_sent
                + current.bytes_recv - prev_recv
            )
            mbps = byte_delta * 8 / elapsed / 1_000_000

            topic = f"network/{interface}/mbps"
            self.mqtt.publish(topic, f"{mbps:.3f}")
