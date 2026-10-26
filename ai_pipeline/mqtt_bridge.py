"""
Runs on the SAME server as the AI pipeline (or standalone). Subscribes
to every device's heartbeat topic and forwards each one to the backend
via HTTP, so /dashboard can show live Pi online/offline status.

    python mqtt_bridge.py
"""
import json
import os

import paho.mqtt.client as mqtt

from event_reporter import report_heartbeat

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
HEARTBEAT_TOPIC_FILTER = "pi/+/heartbeat"  # + wildcard matches any device_id


def on_connect(client, userdata, flags, rc):
    print(f"[mqtt_bridge] connected (rc={rc}), subscribing to '{HEARTBEAT_TOPIC_FILTER}'")
    client.subscribe(HEARTBEAT_TOPIC_FILTER)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        device_id = payload["device_id"]
        report_heartbeat(device_id)
        print(f"[mqtt_bridge] forwarded heartbeat for {device_id}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[mqtt_bridge] bad heartbeat payload on {msg.topic}: {e}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
