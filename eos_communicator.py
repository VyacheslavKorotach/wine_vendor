import os
import json
# import requests
import time
import paho.mqtt.client as mqtt
from eospy.cleos import Cleos

message = 'ON'
topic_sub1 = 'f'
topic_pub1 = 'f2'
eos_endpoint = 'https://eos.greymass.com:443'
mqtt_host = 'korotach.com'
mqtt_user = 'igor'
mqtt_password = 'igor1315'
topic_pub2 = 'f3'
vendor_account = 'wealthysnake'


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


def get_EOS_balance(account):
    ce = Cleos(url=eos_endpoint)
    EOS_balance_list = ce.get_currency_balance(account)
    if EOS_balance_list:
        EOS_balance = float(EOS_balance_list[0].split(' ')[0])
    else:
        EOS_balance = 0
    return EOS_balance


def get_KNYGA_balance(account):
    ce = Cleos(url=eos_endpoint)
    KNYGA_balance_list = ce.get_currency_balance(account, code='knygarium111', symbol='KNYGA')
    if KNYGA_balance_list:
        KNYGA_balance = float(KNYGA_balance_list[0].split(' ')[0])
    else:
        KNYGA_balance = 0
    return KNYGA_balance


def write_to_eos(msg):
    transfer_str = "cleos -u " + eos_node_url + " transfer wealthytiger destitutecat '0.0001 EOS' '" + str(msg) + "'"
    out = os.popen(transfer_str).read()
    print(out)


def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError:
        return False
    return True


def get_last_actions():
    out = {}
    ce = Cleos(url=eos_endpoint)
    actions = ce.get_actions(vendor_account, pos=-1, offset=-12)
    if 'actions' in actions.keys():
        out = actions['actions']
    memos = []
    for s in out:
        receiver = s['action_trace']['receipt']['receiver']
        recv_sequence = s['action_trace']['receipt']['recv_sequence']
        data = s['action_trace']['act']['data']
        if receiver == vendor_account \
                and 'to' in data.keys() \
                and data['to'] == vendor_account \
                and 'from' in data.keys()\
                and 'quantity' in data.keys()\
                and (data['quantity'].find('EOS') != -1 or data['quantity'].find('KNYGA') != -1):
            data['recv_sequence'] = recv_sequence
            memos.append(data)
            # if 'memo' in data.keys() and data['memo'] != "":
            #     if is_json(data['memo']):
            #         d = json.loads(data['memo'])
            #         if d['latitude'] != '':
            #             d['humidity'] = d['humidity_%']
            #             memos.append(d)
            #    memos = [d] + memos
    # memos.reverse()
    return memos


mqttc = mqtt.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
# mqttc.on_log = on_log
mqttc.username_pw_set(mqtt_user, password=mqtt_password)
# Connect
mqttc.connect(mqtt_host, 1883, 60)
# Continue the network loop
# mqttc.loop_forever()
mqttc.loop_start()
time.sleep(1)
last_actions = get_last_actions()
init_action_number = 0
if last_actions:
    last_actions.reverse()
    init_action_number = last_actions[0]['recv_sequence']
print('last processed transaction number is ', init_action_number)
vendor_EOS_balance = get_EOS_balance(vendor_account)
vendor_EOS_balance_initial = vendor_EOS_balance
vendor_KNYGA_balance = get_KNYGA_balance(vendor_account)
vendor_KNYGA_balance_initial = vendor_KNYGA_balance
state = 'Start'

while state != 'Stop':

    # waiting for transaction
    while vendor_EOS_balance == vendor_EOS_balance_initial and vendor_KNYGA_balance == vendor_KNYGA_balance_initial:
        state = 'Waiting for transaction'
        vendor_EOS_balance = get_EOS_balance(vendor_account)
        print('vendor EOS balance = ', vendor_EOS_balance)
        vendor_KNYGA_balance = get_KNYGA_balance(vendor_account)
        print('vendor KNYGA balance = ', vendor_KNYGA_balance)
        #    mqttc.publish(topic_pub2, '1235')
        time.sleep(3)

    # detecting of transaction to process
    state = 'transactions parsing'
    last_actions = get_last_actions()
    print(last_actions)

    state = 'Stop'
