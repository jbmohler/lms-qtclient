from . import api


class TransactionController(api.Controller):
    def values_preset(self):
        pass

    def values_changed(self):
        pass

    def value_changed(self):
        pass

    def balance(self, row):
        pass


class ClientTransactionController(TransactionController):
    def fetch_account_info(self, acc_id):
        pass


class TransactionData:
    def __init__(self, payload):
        content = client.StdPayload(payload)

        self.trans = content.named_table('transaction')
        self.splits = content.named_table('splits')
