import time
import paho.mqtt.client as mqtt

message = 'ON'
topic_sub1 = 'f'
topic_pub1 = 'f2'


def on_connect(mosq, obj, flags, rc):
    global topic_sub1
    mqttc.subscribe(topic_sub1, 0)
    print("rc: " + str(rc))


def on_message(mosq, obj, msg):
    global message
    global topic_pub1
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    message = msg.payload
    mqttc.publish(topic_pub1, msg.payload)


def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))


def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mosq, obj, level, string):
    print(string)


mqtt_host = 'korotach.com'
mqtt_user = 'igor'
mqtt_password = 'igor1315'
mqttc = mqtt.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
#mqttc.on_log = on_log
mqttc.username_pw_set(mqtt_user, password=mqtt_password)
# Connect
mqttc.connect(mqtt_host, 1883, 60)
topic_pub2 = 'f3'
# Continue the network loop
#mqttc.loop_forever()
mqttc.loop_start()
time.sleep(1)

while True:
    print('here we check the EOS wallet and publish if received money')
    mqttc.publish(topic_pub2, '1235')
    time.sleep(15)
