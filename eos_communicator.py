import os
import json
import time
import paho.mqtt.client as mqtt
from eospy.cleos import Cleos
import eospy.cleos
import eospy.keys
import pytz

message = 'ON'
debug = True
topic_sub1 = 'wine_vendor/knygarnya111/device0001/state'
topic_pub1 = 'wine_vendor/knygarnya111/device0001/ctl'
# cmd = {'recv_sequence': 0, 'account': ''}
eos_endpoint = 'https://eos.greymass.com:443'
depth = 33
mqtt_host = 'korotach.com'
mqtt_user = 'igor'
mqtt_password = 'igor1315'
topic_pub2 = 'f3'
vendor_account = 'wealthysnake'
active_privat_key = os.environ['WINE_VENDOR_PRIVAT_KEY']
price = {'EOS': 0.0003, 'KNYGA': 0.0008}
memo_msgs = ["not enough money, the price is: ",
             "It's too much. Take the change back. The price is: ",
             "Thank you! Have a nice day! ;)"]
delay_max = 12  # sec - it's max delay from device


def on_connect(mosq, obj, flags, rc):
    global topic_sub1
    mqttc.subscribe(topic_sub1, 0)
    print("rc: " + str(rc))


def on_message(mosq, obj, msg):
    # get the status string from device
    # {"recv_sequence": 32, "status": "OK"} or {"recv_sequence": 32, "status": "Error"}
    global message
    global topic_pub1
    global state
    global goods_number
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    message = msg.payload
    #    mqttc.publish(topic_pub1, msg.payload)
    json_string = ''
    d = {}
    try:
        json_string = msg.payload.decode('utf8')
    except UnicodeDecodeError:
        print("it was not a ascii-encoded unicode string")
    if json_string != '' and is_json(json_string):
        d = json.loads(json_string)
        if 'status' in d.keys() and d['status'] == 'OK' \
                and 'recv_sequence' in d.keys() and d['recv_sequence'] == goods_number:
            state = 'we successfully have gave goods out'
        else:
            if 'status' in d.keys() and d['status'].find('Error') != -1:
                state = 'We have received the Error code from device.'
            else:
                state = 'We have received a wrong message from device. Stop crypto-barman.'
    if debug: print('state = ', state)


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


def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError:
        return False
    return True


def get_last_actions():
    out = {}
    ce = Cleos(url=eos_endpoint)
    actions = ce.get_actions(vendor_account, pos=-1, offset=-depth)
    if 'actions' in actions.keys():
        out = actions['actions']
    memos = []
    for s in out:
        receiver = s['action_trace']['receipt']['receiver']
        data = s['action_trace']['act']['data']
        if s['action_trace']['act']['name'] == 'transfer' \
                and receiver == vendor_account \
                and 'to' in data.keys() \
                and data['to'] == vendor_account \
                and 'from' in data.keys() \
                and 'quantity' in data.keys() \
                and (data['quantity'].find('EOS') != -1 or data['quantity'].find('KNYGA') != -1):
            data['recv_sequence'] = s['action_trace']['receipt']['recv_sequence']
            data['account'] = s['action_trace']['act']['account']
            memos.append(data)
    # memos.reverse()
    return memos


def refund(action, amount, memo):
    ce = Cleos(url=eos_endpoint)

    arguments = {
        "from": action['to'],  # sender
        "to": action['from'],  # receiver
        "quantity": str(amount) + ' ' + action['quantity'].split(' ')[1],  # In Token
        "memo": memo,
    }
    payload = {
        "account": action['account'],
        "name": 'transfer',
        "authorization": [{
            "actor": vendor_account,
            "permission": 'active',
        }],
    }
    # Converting payload to binary
    data = ce.abi_json_to_bin(payload['account'], payload['name'], arguments)
    # Inserting payload binary form as "data" field in original payload
    payload['data'] = data['binargs']
    # final transaction formed
    trx = {"actions": [payload]}
    import datetime as dt
    trx['expiration'] = str((dt.datetime.utcnow() + dt.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
    # use a string or EOSKey for push_transaction
    # key = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
    # use EOSKey:
    key = eospy.keys.EOSKey(active_privat_key)
    resp = ce.push_transaction(trx, key, broadcast=True)
    # print('------------------------------------------------')
    # print(resp)
    # print('------------------------------------------------')
    return resp


def give_out_goods(recv_sequence, account):
    global state
    #    global cmd
    global topic_pub1
    global goods_number
    goods_number = recv_sequence
    state = 'giving out goods'
    if debug: print('giving out goods')
    tst_start = int(time.time())
    mqttc.publish(topic_pub1, '{"recv_sequence": "' + str(recv_sequence) +
                  '", "account": "' + account + '", "tst": ' + str(tst_start) + '}')
    delay = 0
    while state != "we've gave goods out" and delay < delay_max:
        delay = int(time.time()) - tst_start
        time.sleep(0.5)
    if state != 'we successfully have gave goods out':
        state = 'Error: giving out goods timeout. Stop crypto-barman.'


def money_distribute(price, currency):
    if debug: print('money distributing')
    pass


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
last_processed_action = init_action_number
vendor_EOS_balance = get_EOS_balance(vendor_account)
vendor_EOS_balance_initial = vendor_EOS_balance
vendor_KNYGA_balance = get_KNYGA_balance(vendor_account)
vendor_KNYGA_balance_initial = vendor_KNYGA_balance
state = 'Start'
goods_number = 0

if debug: print('state = ', state)

while state.find('Stop') == -1:

    # waiting for transaction
    while vendor_EOS_balance == vendor_EOS_balance_initial and vendor_KNYGA_balance == vendor_KNYGA_balance_initial:
        state = 'Waiting for transaction'
        time.sleep(3)
        if debug: print('state = ', state)
        vendor_EOS_balance = get_EOS_balance(vendor_account)
        if debug: print('vendor EOS balance = ', vendor_EOS_balance)
        vendor_KNYGA_balance = get_KNYGA_balance(vendor_account)
        if debug: print('vendor KNYGA balance = ', vendor_KNYGA_balance)
        #    mqttc.publish(topic_pub2, '1235')

    # detecting transaction to be processed
    state = 'transactions parsing'
    if debug: print('state = ', state)
    last_actions = get_last_actions()
    if debug: print('last actions: ', last_actions)
    actions_to_process = []
    for n in last_actions:
        if n['recv_sequence'] > last_processed_action:
            actions_to_process.append(n)
    if debug: print('action_to_process: ', actions_to_process)

    # processing transactions
    state = 'processing of transactions'
    if debug: print('state = ', state)
    transaction_resp = {}
    for n in actions_to_process:
        currency = n['quantity'].split(' ')[1]
        amount = float(n['quantity'].split(' ')[0])
        if amount < price[currency]:
            transaction_resp = refund(n, amount,
                                      memo_msgs[0] + str(price[currency]) + ' ' + currency)
        elif amount > price[currency]:
            transaction_resp = refund(n, amount - price[currency],
                                      memo_msgs[1] + str(price[currency]) + ' ' + currency)
            give_out_goods(n['recv_sequence'], n['account'])
            money_distribute(price[currency], currency)
        else:
            transaction_resp = refund(n, 0.0001,
                                      memo_msgs[2] + str(price[currency]) + ' ' + currency)
            give_out_goods(n['recv_sequence'], n['account'])
            money_distribute(price[currency] - 0.0001, currency)
        if debug: print('resp: ', transaction_resp)

    state = 'Stop'
    if debug: print('state = ', state)
