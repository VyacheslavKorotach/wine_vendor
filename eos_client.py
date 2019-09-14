from typing import List

import eospy
import pytz
from eospy.cleos import Cleos
from abc import ABC, abstractmethod
import datetime as dt

from transaction import Transaction


class CryptoBalance(ABC):

    @abstractmethod
    def get_balance(self, account) -> float:
        pass

    @abstractmethod
    def update_balance(self):
        pass


# TODO: split client into CLIENT & BALANCE
class EOSBalance(CryptoBalance):
    MEMO_MSGS = ["Not enough money, the price of wine is: ",
                 "It's too much. Take the change back. The price of wine is: ",
                 "Thank you! Have a nice day! ;)", "Something went wrong. Take your money back. "]
    # TODO: move this to appropriate place
    CRYPTO_PRICE = {'EOS': 0.0003, 'KNYGA': 0.0008}
    OFFSET = 33

    def __init__(self, eos_endpoint: str, transaction: Transaction, private_key: str):
        self.__private_key = private_key
        self.eos_endpoint = eos_endpoint
        self.cleos = Cleos(url=eos_endpoint)
        self.transaction = transaction

    def get_balance(self, account) -> float:
        eos_balances: List = self.cleos.get_currency_balance(account)
        if eos_balances:
            eos_balance = float(eos_balances[0].split(' ')[0])
        else:
            eos_balance = 0.0
        return eos_balance

    def get_last_actions(self):
        out = {}
        actions = self.cleos.get_actions(self.transaction.bartender_account, pos=-1, offset=-EOSBalance.OFFSET)
        if actions.get('actions', None):
            out = actions['actions']
        return [data for data in out if self.transaction.check_transaction(data)]

    def refund(self, action: dict, amount: float, memo: str):
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
                "actor": self.transaction.bartender_account,
                "permission": 'active',
            }],
        }
        data = self.cleos.abi_json_to_bin(payload['account'], payload['name'], arguments)
        payload['data'] = data['binargs']
        trx = {"actions": [payload],
               'expiration': str((dt.datetime.utcnow() + dt.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))}
        key = eospy.keys.EOSKey(self.__private_key)
        resp = self.cleos.push_transaction(trx, key, broadcast=True)
        return resp.get('transaction_id', None)


class KNYGABalance(EOSBalance):

    def get_balance(self, account) -> float:
        knyga_balances: List = self.cleos.get_currency_balance(account, code='knygarium111', symbol='KNYGA')
        if knyga_balances:
            knyga_balance = float(knyga_balances[0].split(' ')[0])
        else:
            knyga_balance = 0
        return knyga_balance