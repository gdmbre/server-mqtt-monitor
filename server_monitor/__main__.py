"""CLI entry point for server-mqtt-monitor, with a numbered single-check test menu."""

import argparse
import shutil
import tempfile
from pathlib import Path

from .config import load_settings
from .checks import AVAILABLE_CHECKS


class PreviewMqtt:
    """Show what a check would publish without connecting to the MQTT broker."""

    def __init__(self, settings):
        self.settings = settings

    def publish(self, topic_name, payload, *, retain=False):
        prefix = self.settings.topic_prefix
        topic = self.settings.topics.get(topic_name, topic_name).strip("/")
        full_topic = f"{prefix}/{topic}" if prefix else topic
        print(f"[MQTT -> {full_topic}] {payload}", flush=True)

    def info(self, message):
        return self.publish("info", message)

    def warning(self, message):
        return self.publish("warning", message)


def test_menu(settings):
    checks = list(AVAILABLE_CHECKS)
    if not checks:
        print("Нет зарегистрированных плагинов.")
        return 1

    print("\nДоступные проверки (тест без отправки MQTT):\n")
    for index, check_class in enumerate(checks, 1):
        state = "включён" if settings.check_enabled(check_class.NAME) else "выключен"
        print(f" {index:2}. {check_class.NAME:<20} [{state}]")
    print("  0. Выход\n")

    try:
        while True:
            choice = input("Номер плагина для теста: ").strip()
            if choice == "0":
                return 0
            if choice.isdecimal() and 1 <= int(choice) <= len(checks):
                selected = checks[int(choice) - 1]
                break
            print("Введите номер из списка или 0 для выхода.")
    except (KeyboardInterrupt, EOFError):
        print("\nОтменено.")
        return 130

    print(f"\nЗапускаем только {selected.NAME}...", flush=True)
    try:
        check = selected(settings, PreviewMqtt(settings))

        # Test the Trivy check without overwriting its real CVE history.
        # Copy the existing baseline into a temporary file if one is present.
        with tempfile.TemporaryDirectory(prefix="monitor-check-") as tmpdir:
            if check.NAME == "trivy":
                state_path = Path(check.config.get(
                    "state_file", "/var/lib/server-monitor/trivy-state.json"
                ))
                test_path = Path(tmpdir) / "trivy-state.json"
                if state_path.is_file():
                    shutil.copyfile(state_path, test_path)
                check.config = {**check.config, "state_file": str(test_path)}

            check.run()

            # Long-running checks such as Trivy start a background worker.
            # Keep the test process alive until this particular check finishes.
            worker = getattr(check, "_worker", None)
            if worker is not None:
                worker.join()

    except KeyboardInterrupt:
        print("\nТест прерван.")
        return 130
    except Exception as exc:
        print(f"ОШИБКА в {selected.NAME}: {exc}", flush=True)
        return 1

    print(f"\nТест {selected.NAME} завершён (проверь сообщения выше).")
    return 0


def check_config(path):
    try:
        settings = load_settings(path)
        mqtt = settings.mqtt

        broker = mqtt.get("broker")
        if not isinstance(broker, str) or not broker.strip():
            raise ValueError("mqtt.broker должен быть непустой строкой")

        tls = mqtt.get("tls", False)
        if not isinstance(tls, bool):
            raise ValueError("mqtt.tls должен быть true или false")

        port = mqtt.get("port", 8883 if tls else 1883)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("mqtt.port должен быть числом от 1 до 65535")

        for name, config in settings.raw.get("checks", {}).items():
            if not isinstance(config, dict):
                raise ValueError(f"checks.{name} должен быть таблицей")

            if "enabled" in config and not isinstance(config["enabled"], bool):
                raise ValueError(f"checks.{name}.enabled должен быть true/false")

            if "interval" in config:
                interval = config["interval"]
                if type(interval) not in (int, float) or interval <= 0:
                    raise ValueError(f"checks.{name}.interval должен быть больше 0")

        print("✓ Синтаксис TOML корректен")
        print("✓ Настройки MQTT корректны")
        print(f"✓ Сервер: {broker}")
        print(f"✓ Порт: {port}")
        print(f"✓ TLS: {'включён' if tls else 'выключен'}")
        print(f"✓ Проверок настроено: {len(settings.raw.get('checks', {}))}")
        print("\nКонфигурация корректна.")
        return 0

    except Exception as exc:
        print(f"✗ Ошибка конфигурации: {exc}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Server MQTT monitor")
    parser.add_argument(
        "--config", default="/etc/server-monitor/config.toml",
        help="Path to TOML config file",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Select a registered check by number and run it once without MQTT",
    )

    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Проверить конфигурацию без запуска мониторинга",
    )
    args = parser.parse_args()

    if args.check_config:
        raise SystemExit(check_config(args.config))

    settings = load_settings(args.config)
    if args.test:
        raise SystemExit(test_menu(settings))

    # Normal service mode remains unchanged.
    from .mqtt_client import MqttPublisher
    from .runner import MonitorRunner

    mqtt = MqttPublisher(settings)
    mqtt.connect()
    try:
        runner = MonitorRunner(settings, mqtt)
        runner.run_forever()
    finally:
        mqtt.disconnect()


if __name__ == "__main__":
    main()
