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
