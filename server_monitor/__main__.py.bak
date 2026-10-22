import argparse

from .config import load_settings
from .mqtt_client import MqttPublisher
from .runner import MonitorRunner


def main():
    parser = argparse.ArgumentParser(description="Server MQTT monitor")
    parser.add_argument(
        "--config",
        default="/etc/server-monitor/config.toml",
        help="Path to TOML config file",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    mqtt = MqttPublisher(settings)
    mqtt.connect()

    try:
        runner = MonitorRunner(settings, mqtt)
        runner.run_forever()
    finally:
        mqtt.disconnect()


if __name__ == "__main__":
    main()
