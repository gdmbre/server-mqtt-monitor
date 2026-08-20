import time
import psutil

from .base import BaseCheck


class NetworkSpeedCheck(BaseCheck):
    NAME = "network_speed"

    def __init__(self, settings, mqtt):
        super().__init__(settings, mqtt)
        self.previous = {}
        self.missing_interfaces = set()

    def run(self):
        interfaces = self.config.get("interfaces")

        if not interfaces:
            single = self.config.get("interface")
            interfaces = [single] if single else []

        now = time.monotonic()
        counters = psutil.net_io_counters(pernic=True)

        for interface in interfaces:

            # Интерфейс отсутствует
            if interface not in counters:

                # Сообщаем только один раз
                if interface not in self.missing_interfaces:
                    self.mqtt.warning(
                        f"Network interface {interface} not found on "
                        f"{self.settings.device_name}"
                    )

                    self.missing_interfaces.add(interface)

                # Старые данные больше не актуальны
                self.previous.pop(interface, None)

                continue

            # Интерфейс появился после отсутствия
            if interface in self.missing_interfaces:
                self.mqtt.info(
                    f"Network interface {interface} recovered on "
                    f"{self.settings.device_name}"
                )

                self.missing_interfaces.remove(interface)

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

            self.mqtt.publish(
                topic,
                f"{mbps:.3f}"
            )
