import paho.mqtt.client as mqtt
import ssl


class MqttPublisher:
    def __init__(self, settings):
        self.settings = settings

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.mqtt.get("client_id", "server-monitor"),
        )

        username = settings.mqtt.get("username")
        password = settings.mqtt.get("password")

        if username:
            self.client.username_pw_set(username, password)

    def connect(self):
        use_tls = self.settings.mqtt.get("tls", False)

        if use_tls:
            self.client.tls_set_context(
                ssl.create_default_context()
            )

        port = int(
            self.settings.mqtt.get(
                "port", 8883 if use_tls else 1883
            )
        )

        self.client.connect(
            self.settings.mqtt["broker"],
            port,
            keepalive=int(
                self.settings.mqtt.get("keepalive", 60)
            ),
        )

        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def topic(self, name: str) -> str:
        prefix = self.settings.topic_prefix
        topic_name = self.settings.topics.get(name, name).strip("/")

        if prefix:
            return f"{prefix}/{topic_name}"

        return topic_name

    def publish(self, topic_name: str, payload, *, retain: bool = False):
        topic = self.topic(topic_name)
        result = self.client.publish(topic, str(payload), retain=retain)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"MQTT publish failed: topic={topic}, rc={result.rc}")

        return result

    def info(self, message: str):
        return self.publish("info", message)

    def warning(self, message: str):
        return self.publish("warning", message)
