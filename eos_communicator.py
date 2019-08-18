import os
import time
import paho.mqtt.client as mqtt
from eospy.cleos import Cleos
import eospy.cleos
import eospy.keys
import pytz

from mqtt_client import WineMQTTClient
from wine_vendor_state import WineVendorState, BartenderBalanceState
from .eos_client import EOSBalance, KNYGABalance
from .transaction import Transaction

message = 'ON'
TOPIC_SUB1 = 'wine_vendor/knygarnya111/device0001/state'
TOPIC_PUB1 = 'wine_vendor/knygarnya111/device0001/ctl'
# cmd = {'recv_sequence': 0, 'account': ''}
EOS_ENDPOINT = 'https://eos.greymass.com:443'
OFFSET = 33
MQTT_HOST = 'korotach.com'
MQTT_USER = 'igor'
MQTT_PASSWORD = 'igor1315'
TOPIC_PUB = 'f3'
BARTENDER_ACCOUNT = 'wealthysnake'
ACTIVE_PRIVATE_KEY = os.environ['WINE_VENDOR_PRIVAT_KEY']
DELAY = 21  # sec - it's max delay from device
VENDOR_ACCOUNT = 'wealthytiger'
VENDOR_PART = 0.5
OWNER_ACCOUNT = 'vyacheslavko'
OWNER_PART = 0.33
SUPPORT_ACCOUNT = 'destitutecat'
SUPPORT_PART = 1 - VENDOR_PART - OWNER_PART


def on_connect(mosq, obj, flags, rc):
    mqttc.subscribe(TOPIC_SUB1, 0)
    print("rc: " + str(rc))



def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))


def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mosq, obj, level, string):
    print(string)


def get_last_actions():
    transaction = Transaction(BARTENDER_ACCOUNT)
    out = {}
    ce = Cleos(url=EOS_ENDPOINT)
    actions = ce.get_actions(BARTENDER_ACCOUNT, pos=-1, offset=-OFFSET)
    if 'actions' in actions.keys():
        out = actions['actions']
    return [data for data in out if transaction.check_transaction(data)]


def refund(action, amount, memo):
    ce = Cleos(url=EOS_ENDPOINT)

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
            "actor": BARTENDER_ACCOUNT,
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
    key = eospy.keys.EOSKey(ACTIVE_PRIVATE_KEY)
    resp = ce.push_transaction(trx, key, broadcast=True)
    return 'transaction_id' in resp.keys()


def send_tokens(token, account_to, quantity, memo):
    contract_accounts = {'EOS': 'eosio.token', 'KNYGA': 'knygarnya111'}
    ce = Cleos(url=EOS_ENDPOINT)

    arguments = {
        "from": BARTENDER_ACCOUNT,  # sender
        "to": account_to,  # receiver
        "quantity": str(quantity) + ' ' + token,  # In Token
        # "quantity": 0.0001,  # In Token
        "memo": memo,
    }
    payload = {
        "account": contract_accounts[token],
        # "account": 'eosio.token',
        "name": 'transfer',
        "authorization": [{
            "actor": BARTENDER_ACCOUNT,
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
    key = eospy.keys.EOSKey(ACTIVE_PRIVATE_KEY)
    resp = ce.push_transaction(trx, key, broadcast=True)
    return 'transaction_id' in resp.keys()


def give_out_goods(recv_sequence, account):
    global state
    global goods_number
    goods_number = recv_sequence
    state = 'giving out goods'
    tst_start = int(time.time())
    mqttc.publish(TOPIC_PUB1, '{"recv_sequence": ' + str(recv_sequence) +
                  ', "account": "' + account + '", "tst": ' + str(tst_start) + '}')
    delay = 0
    while state != 'we successfully have gave goods out' and delay < DELAY:
        delay = int(time.time()) - tst_start
        time.sleep(0.5)
    if state != 'we successfully have gave goods out':
        state = 'Error: giving out goods timeout. Stop crypto-bartender.'
        return False
    else:
        return True


def money_distribute(income, token):
    ret = True
    ret = send_tokens(token, VENDOR_ACCOUNT, round(income * VENDOR_PART, 4), 'for wine transaction #' + str(goods_number))
    time.sleep(3)
    ret = ret and send_tokens(token, OWNER_ACCOUNT, round(income * OWNER_PART, 4), 'for wine transaction #' + str(goods_number))
    time.sleep(3)
    ret = ret and send_tokens(token, SUPPORT_ACCOUNT, round(round(income, 4) - round(income * VENDOR_PART, 4) - round(income * OWNER_PART, 4), 4), 'for wine transaction #' + str(goods_number))
    return ret


def main():
    eos_balance = EOSBalance(EOS_ENDPOINT)
    knyga_balance = KNYGAClient(EOS_ENDPOINT)
    eos_client = "EOS_Client()"

    balance_state = BartenderBalanceState(eos_balance, knyga_balance)
    vendor_state = WineVendorState(0, balance_state, eos_client)

    def on_message(mosq, obj, msg):
        """
        MQTT-callback, get the status string from device
        :param mosq:
        :param obj:
        :param msg: msg.payload - {"recv_sequence": 32, "status": "OK"} or {"recv_sequence": 32, "status": "Error"}
        :return: None
        """
        print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        decoded_msg: dict = WineMQTTClient.decode(msg)
        vendor_state.set_mqtt_message_state(decoded_msg)

    mqttc = mqtt.Client()
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.username_pw_set(MQTT_USER, password=MQTT_PASSWORD)
    mqttc.connect(MQTT_HOST, 1883, 60)
    mqttc.loop_start()

    bartender_eos_balance = eos_client.get_balance(BARTENDER_ACCOUNT)
    bartender_eos_balance_initial = bartender_eos_balance
    bartender_knyga_balance = knyga_client.get_balance(BARTENDER_ACCOUNT)
    bartender_knyga_balance_initial = bartender_knyga_balance

    while True:

        while state.find('Stop') != -1:
            time.sleep(2)
            pass

        # waiting for transaction
        while bartender_EOS_balance == bartender_EOS_balance_initial \
                and bartender_KNYGA_balance == bartender_KNYGA_balance_initial:
            state = 'Waiting for transaction'
            time.sleep(3)
            bartender_EOS_balance = get_EOS_balance(BARTENDER_ACCOUNT)
            bartender_KNYGA_balance = get_KNYGA_balance(BARTENDER_ACCOUNT)

        # detecting transaction to be processed
        state = 'transactions parsing'
        last_actions = get_last_actions()
        actions_to_process = []
        for n in last_actions:
            if n['recv_sequence'] > last_processed_action:
                actions_to_process.append(n)

        # processing transactions
        state = 'processing of transactions'
        for n in actions_to_process:
            currency = n['quantity'].split(' ')[1]
            amount = float(n['quantity'].split(' ')[0])
            if amount < EOSBalance.CRYPTO_PRICE[currency] and refund(n, amount, EOSBalance.MEMO_MSGS[0] + str(
                    EOSBalance.CRYPTO_PRICE[currency]) + ' ' + currency):
                state = "Not enough money had been sent to give goods out in transaction # " \
                        + str(n['recv_sequence']) + ". Money was returned"
            elif amount > EOSBalance.CRYPTO_PRICE[currency] and refund(n,
                                                                       round(amount - EOSBalance.CRYPTO_PRICE[currency],
                                                                            4),
                                                                       EOSBalance.MEMO_MSGS[1] + str(
                                                                          EOSBalance.CRYPTO_PRICE[
                                                                              currency]) + ' ' + currency):
                state = "Too much money had been sent in transaction # " \
                        + str(n['recv_sequence']) + ". Extra money was returned."
                if give_out_goods(n['recv_sequence'], n['from']):
                    if money_distribute(EOSBalance.CRYPTO_PRICE[currency], currency):
                        state = "Money and goods successfully distributed according to transaction # " + str(
                            n['recv_sequence'])
                else:
                    if refund(n, round(EOSBalance.CRYPTO_PRICE[currency], 4),
                              EOSBalance.MEMO_MSGS[3] + str(EOSBalance.CRYPTO_PRICE[currency]) + ' ' + currency):
                        state = "Something went wrong. Goods can't be delivered. Error processing transaction # " \
                                + n['account'] + ". Money was returned. Stop the crypto-barmen."
                    else:
                        state = "Something went wrong. Goods can't be delivered. Error processing transaction # " \
                                + n['account'] + ". Money can't be returned. Stop the crypto-barmen."
            else:  # It was sent a right price
                if give_out_goods(n['recv_sequence'], n['from']):
                    if money_distribute(round(EOSBalance.CRYPTO_PRICE[currency] - 0.0001, 4), currency):
                        state = "Money and goods successfully distributed according to transaction # " + str(
                            n['recv_sequence'])
                        refund(n, 0.0001,
                               EOSBalance.MEMO_MSGS[2] + str(EOSBalance.CRYPTO_PRICE[currency]) + ' ' + currency)
                else:
                    if refund(n, round(EOSBalance.CRYPTO_PRICE[currency], 4),
                              EOSBalance.MEMO_MSGS[3] + str(EOSBalance.CRYPTO_PRICE[currency]) + ' ' + currency):
                        state = "Something went wrong. Goods can't be delivered. Error processing transaction # " \
                                + n['account'] + ". Money was returned. Stop the crypto-barmen."
                    else:
                        state = f"Something went wrong. Goods can't be delivered. Error processing transaction # {n['account']}. Money can't be returned. Stop the crypto-barmen."
            last_processed_action = n['recv_sequence']

        state = 'Stop'


last_actions = get_last_actions()
init_action_number = 0
if last_actions:
    last_actions.reverse()
    init_action_number = last_actions[0]['recv_sequence']
print('last processed transaction number is ', init_action_number)
last_processed_action = init_action_number
