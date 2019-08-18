class Transaction:
    def __init__(self, bartender_account: str):
        self.bartender_account: str = bartender_account

    def check_transaction(self, transaction: dict) -> bool:
        action_trace = transaction['action_trace']
        receipt = action_trace['receipt']
        receiver = receipt['receiver']
        action = action_trace['act']
        data = action['data']
        quantity = data['quantity']
        if action['name'] != 'transfer':
            return False
        if receiver != self.bartender_account:
            return False
        if data['to'] is None or data['from'] is None or quantity is None:
            return False
        if not ('EOS' in quantity) or not ('KNYGA' in quantity):
            return False
        data['recv_sequence'] = receipt['recv_sequence']
        data['account'] = action['account']
        return True
