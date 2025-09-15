import paho.mqtt.client as mqtt
import random
import time
import string
import json




broker = "dev-mqtt.rainscales.com"
port = 8003

def generate_topic():
    org = "org" + ''.join(random.choices(string.ascii_letters, k=7))
    site = "site" + ''.join(random.choices(string.ascii_letters, k=6))
    area = "area" + ''.join(random.choices(string.ascii_letters, k=6))
    device_id = ''.join(random.choices(string.ascii_letters, k=10))
    return f"iot/{org}/{site}/{area}/{device_id}/telemetry/v1" 

           
def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client_id = f"publish-{random.randint(0,1000)}"
    print(client_id)
    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def publish(client):
    try:
        while True :
            topic = generate_topic()
            data = {
    "schema_version": "1.1.0",
    "device_id": "QM30VT2-0001",
    "ts": "2025-09-03T13:54:14.000Z",
    "seq": 128773,
    "window_start": "2025-09-03T13:54:13.000Z",  "window_end": "2025-09-03T13:54:14.000Z",

    "vibration": {
	    "units": {
  	        "acceleration": "g",
  	        "velocity": "mm/s"
	    },
	"axes": ["x", "z"],
	"sample_rate_hz": 1024,
	"summary": {
  	     "x": {
    	        "rms_velocity_mms": -0.001,
    	        "rms_acceleration_g": 1.739,
    	        "peak_velocity_mms": -0.001,
    	        "peak_acceleration_g": 1.043,
    	        "peak_velocity_component_mms": 9.7,
    	        "kurtosis": -0.001,
    	        "crest_factor": 28.797,
    	        "high_freq_rms_acc_g": 0.036
  	    },
  	    "z": {
    	        "rms_velocity_mms": -27.209,
    	        "rms_acceleration_g": 0.439,
    	        "peak_velocity_mms": -11.333,
    	        "peak_acceleration_g": 0.246,
    	        "peak_velocity_component_mms": 9.7,
    	        "kurtosis": -0.001,
    	        "crest_factor": 20.295,
    	        "high_freq_rms_acc_g": 0.012
  	    }
	},
	"raw": {
  	"encoding": "float32",
  	"x": "base64:...",
  	"z": "base64:...",
  	"num_samples": 1024,
  	"duration_ms": 1000
	}
  },
 
  "temperature": {
	"unit": "C",
	"instant": 32.45
  },
 
  "health": {
	"battery_v": 3.89,
	"rssi_dbm": -67,
	"errors": []
  }
}
            client.publish(topic, json.dumps(data))
            print(f"Publishing Data: {data} ")
            print(f"published to topic: {topic} ")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopped")
        client.disconnect()


def run():
    client = connect_mqtt()
    client.loop_start()
    publish(client)
    client.loop_stop()


if __name__ == '__main__':
    run()