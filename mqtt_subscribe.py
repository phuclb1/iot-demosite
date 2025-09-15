import paho.mqtt.client as mqtt
from datetime import datetime
import random
import influxdb_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import os
import json




#token = os.environ.get("INFLUXDB_TOKEN")
token = "eHknf5LcWds3hdixmQHyaXHBaCvPc9sY2Wgr9-yv57evV3vmGAyhW6bcFnuhYs1NadbCt7pKUsTPyoMdIVqi9Q=="
org = "test_org"
url = "http://localhost:8086"
write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
bucket = "test_bucket"
write_api = write_client.write_api(write_options=SYNCHRONOUS)




broker = 'dev-mqtt.rainscales.com'
port = 8003
topic = "iot/+/+/+/+/telemetry/v1" 
client_id = f'subscribe-{random.randint(0, 100)}'



def connect_mqtt() -> mqtt:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    mqtt_client = mqtt.Client(client_id=client_id)
    # client.username_pw_set(username, password)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(broker, port)
    return mqtt_client


def parse_vibration_data(vibration_data, device_id, timestamp):
    points = []
    
    sample_rate = vibration_data.get('sample_rate_hz', 0)
    axes = vibration_data.get('axes', [])
    
    if 'summary' in vibration_data:
        for axis in axes:
            if axis in vibration_data['summary']:
                axis_data = vibration_data['summary'][axis]
                
                point = Point("vibration_summary") .tag("device_id", device_id) .tag("axis", axis) .time(timestamp, WritePrecision.MS)
                
                for field_name, value in axis_data.items():
                    if isinstance(value, (int, float)): 
                        point = point.field(field_name, value)
                
                point = point.field("sample_rate_hz", sample_rate)
                points.append(point)
        
    return points


def parse_payload(payload):
    points = []

    device_id = payload.get('device_id', 'unknown')
    timestamp_str = payload.get('ts')
    seq = payload.get('seq')
    
    timestamp = None
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()
    
    main_point = Point("device_data").tag("device_id", device_id).time(timestamp, WritePrecision.MS)
    
    if seq is not None:
        main_point = main_point.field("seq", seq)
    
    if 'schema_version' in payload:
        main_point = main_point.tag("schema_version", payload['schema_version'])
    
    points.append(main_point)
    
    # Process vibration data
    if 'vibration' in payload:
        vibration_points = parse_vibration_data(payload['vibration'], device_id, timestamp)
        points.extend(vibration_points)

    # Process temperature data
    if 'temperature' in payload:
        temp_data = payload['temperature']
        point = Point("temperature") .tag("device_id", device_id).time(timestamp, WritePrecision.MS)
        
        if 'instant' in temp_data:
            point = point.field("temperature", temp_data['instant'])
        
        if 'unit' in temp_data:
            point = point.tag("unit", temp_data['unit'])
        
        points.append(point)
    
    # Process health data
    if 'health' in payload:
        health_data = payload['health']
        point = Point("device_health") .tag("device_id", device_id) .time(timestamp, WritePrecision.MS)
        
        for field_name, value in health_data.items():
            if field_name != 'errors' and isinstance(value, (int, float)):
                point = point.field(field_name, value)
                
        points.append(point)
    
    return points

def subscribe(mqtt_client: mqtt):
    def on_message(mqtt_client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            points = parse_payload(payload)
            
            for point in points:
                write_api.write(bucket=bucket, org=org, record=point)
            
            print(f"Processed {len(points)} data points from device {payload.get('device_id', 'unknown')}")
            print(f" Recieved: {msg.payload.decode()}")
            print(f"Received from topic: {msg.topic}")
            
        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Payload: {msg.payload.decode()}")

    mqtt_client.subscribe(topic)
    mqtt_client.on_message = on_message


def run():
    mqtt_client = connect_mqtt()
    subscribe(mqtt_client)
    mqtt_client.loop_forever()


if __name__ == '__main__':
    run()


