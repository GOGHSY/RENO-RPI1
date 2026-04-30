import paho.mqtt.client as mqtt

BROKER_IP = "127.0.0.1"  # Broker Pi itself
PORT = 1883
TOPIC = "test/topic"

def on_message(client, userdata, msg):
    print("Broker received:", msg.payload.decode())

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=60)
client.connect(BROKER_IP, PORT)
client.subscribe(TOPIC)
print("Broker subscriber listening...")
client.loop_forever()
