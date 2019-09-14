import enum
import time
from typing import List

from eos_client import EOSBalance, KNYGABalance
from utils import format_message


class State(enum.Enum):
    START = 1
    WRONG_MSG_STOP = 2
    STOP = 3
    GOODS_GIVEN_SUCCESS = 4
    RESTART = 5
    DEVICE_ERROR = 6
    PROCESS_TRANSACTION = 7


class BartenderBalanceState:
    def __init__(self, eos_client: EOSBalance, knyga_client: KNYGABalance, account: str):
        self.eos_client = eos_client
        self.knyga_client = knyga_client
        self.account = account
        self.balances: dict = {
            "EOS": self.eos_client,
            "KNYGA": self.knyga_client
        }

    def is_balance_changed(self) -> bool:
        if self.eos_client.get_balance(self.account) > self.balances["EOS"] or self.knyga_client.get_balance(
                self.account) > self.balances["KNYGA"]:
            return True
        else:
            return False

    def update_balances(self):
        for i in self.balances:
            i.update_balance()


class WineVendorState:
    def __init__(self, last_processed_action: int, bartender_balance_state: BartenderBalanceState,
                 eos_client: EOSBalance):
        self._eos_client = eos_client
        self._state = State.START
        self.last_processed_action = last_processed_action
        self._state_map = {
            State.START: self.wait_stopped,
            State.PROCESS_TRANSACTION: self.wait_pending_transaction
        }
        self._bartender_balance_state = bartender_balance_state

    @property
    def state(self):
        return self.state

    def set_mqtt_message_state(self, decoded_msg: dict):
        if decoded_msg['status']:
            status = decoded_msg['status']
            if status == 'OK' and decoded_msg.get('recv_sequence', None) and decoded_msg[
                'recv_sequence'] == goods_number:
                self.state = State.GOODS_GIVEN_SUCCESS
            elif decoded_msg['status'].find('Error') != -1:
                self.state = State.DEVICE_ERROR
            elif decoded_msg['status'].find('Restart') != -1:
                self.state = State.RESTART
            else:
                self.state = State.WRONG_MSG_STOP
        else:
            self.state = State.STOP

    def wait_pending_transaction(self):
        while not self._bartender_balance_state.is_balance_changed():
            print("Waiting for transaction")
            time.sleep(3)
        actions = self.parse_pending_transaction()

    # TODO: reduce this function by introducing PaymentProcessor
    def process_transaction(self, actions: List):
        for n in actions:
            currency = n['quantity'].split(' ')[1]
            amount = float(n['quantity'].split(' ')[0])
            if amount < EOSBalance.CRYPTO_PRICE[currency] and self._eos_client.refund(
                    n,
                    amount,
                    format_message(EOSBalance.MEMO_MSGS[0], str(EOSBalance.CRYPTO_PRICE[currency]), currency)
            ):
                print(f"Not enough money had been sent to give goods out in transaction # {n['recv_sequence']}. Money was returned")
            elif amount > EOSBalance.CRYPTO_PRICE[currency] and self._eos_client.refund(
                    n,
                    round(amount - EOSBalance.CRYPTO_PRICE[currency], 4),
                    format_message(EOSBalance.MEMO_MSGS[1], str(EOSBalance.CRYPTO_PRICE[currency]), currency)
            ):
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

    def parse_pending_transaction(self) -> List:
        last_actions = self._eos_client.get_last_actions()
        actions_to_process = [action for action in last_actions if action['recv_sequence'] > self.last_processed_action]
        return actions_to_process

    @state.setter
    def state(self, state: State):
        self._state = state

    def check_stopped(self) -> bool:
        if self.state == State.STOP or self.state == State.WRONG_MSG_STOP:
            return True

    def wait_stopped(self):
        while self.check_stopped():
            time.sleep(2)
        self.state = State.WAITING

    def loop_state(self):
        while True:
            self._state_map[self.state]()
