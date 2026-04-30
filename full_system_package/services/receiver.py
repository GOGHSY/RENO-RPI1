import paho.mqtt.client as mqtt
import json
import sys
sys.path.append('/home/suprabha/full_system')

from full_system_package.database.influx_client import InfluxLogger

MQTT_BROKER = "127.0.0.1"
MQTT_PORT   = 1883
MQTT_TOPIC  = "reno/water/treatment/010"

influx = InfluxLogger()

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to {MQTT_TOPIC}")

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode()
        data = json.loads(payload)

        print("\n--- Sensor Data Received ---")
        for key, value in data.items():
            print(f"  {key:<15}: {value}")

        influx.log_treatment(data)
        print("✓ Logged to InfluxDB")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"Disconnected, reason: {reason_code}")

def start_receiver():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print("Listening for water treatment data...")
    client.loop_forever()
