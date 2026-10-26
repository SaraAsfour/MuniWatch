"""
Runs ON THE RASPBERRY PI. Publishes a small JSON heartbeat to the MQTT
broker every HEARTBEAT_INTERVAL_SECONDS, matching the "Pi Heartbeat &
Alert Data" flow in the architecture diagram.

Setup on the Pi:
    pip install paho-mqtt --break-system-packages
    export MQTT_BROKER_HOST=<server-ip-running-mosquitto>
    export DEVICE_ID=raspberry-pi-01
    python3 heartbeat_publisher.py
"""
import json
import os
import time

import paho.mqtt.client as mqtt

DEVICE_ID = os.getenv("DEVICE_ID", "raspberry-pi-01")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "20"))
TOPIC = f"pi/{DEVICE_ID}/heartbeat"


def main():
    client = mqtt.Client(client_id=DEVICE_ID)
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"Publishing heartbeats to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} on topic '{TOPIC}'")
    try:
        while True:
            payload = json.dumps({"device_id": DEVICE_ID, "timestamp": time.time()})
            client.publish(TOPIC, payload, qos=0)
            print(f"[heartbeat] {payload}")
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
