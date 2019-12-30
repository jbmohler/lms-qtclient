from PySide2 import QtWidgets
import client.qt as qt
import apputils
import apputils.widgets as widgets
from . import widgets as pywid
from . import mxc

URL_BASE = 'api/transaction/{}'
URL_BASE2 = 'api/transactions/list'

class SplitsTable(mxc.ModelRow):
    def _rtlib_init_(self):
        if self.sum == None:
            self._debit = None
            self._credit = None
        else:
            self._debit = self.sum if self.sum > 0 else None
            self._credit = -self.sum if self.sum < 0 else None

    @property
    def account(self):
        return pywid.AccountMiniInfo(self.account_id, self.acc_name)

    @account.setter
    def account(self, v):
        self.account_id = v.id
        self.acc_name = v.acc_name

    @property
    def debit(self):
        try:
            return self._debit
        except:
            return None

    @debit.setter
    def debit(self, v):
        self._debit = v
        self.sum = self._debit if self._debit != None else 0. - \
                    self._credit if self._credit != None else 0.

    @property
    def credit(self):
        try:
            return self._credit
        except:
            return None

    @credit.setter
    def credit(self, v):
        self._credit = v
        self.sum = self._debit if self._debit != None else 0. - \
                    self._credit if self._credit != None else 0.

class TransactionCore:
    def __init__(self):
        pass

    @classmethod
    def from_endpoint(cls, controller, content):
        self = cls()
        self.trantable = content.named_table('trans', mixin=mxc.ModelRow)
        self.trantable.DataRow.controller = controller
        self.tranrow = self.trantable.rows[0]
        self.splittable = content.named_table('splits', mixin=SplitsTable)
        self.splittable.DataRow.controller = controller
        return self

    def http_files(self):
        return {\
                'trans': self.trantable.as_http_post_file(),
                'splits':
                self.splittable.as_http_post_file(inclusions=['account_id', 'sum', 'sid'])}

    def ascii_repr(self):
        lines = []
        if self.tranrow.trandate is not None:
            lines.append("Date:  {0}".format(self.tranrow.trandate))
        if self.tranrow.tranref not in [None, ""]:
            lines.append("Reference:  {0}".format(self.tranrow.tranref))
        if self.tranrow.payee not in [None, ""]:
            lines.append("Payee:  {0}".format(self.tranrow.payee))
        if self.tranrow.memo not in [None, ""]:
            lines.append("Memo:  {0}".format(self.tranrow.memo))
        lines.append("-"*(20+1+12+1+12))
        for x in self.splittable.rows:
            lines.append("{0.account:<20} {0.debit:12.2f} {0.credit:12.2f}".format(x))
        lines.append("-"*(20+1+12+1+12))

        return '\n'.join(lines)

class TransactionEditor(qt.ObjectDialog):
    """
    >>> app = apputils.test_app()
    >>> t = TransactionEditor()
    >>> t.exec_()
    1
    """

    ID = 'transaction-editor'
    TITLE = 'PyHacc Transaction'

    def __init__(self, parent=None):
        super(TransactionEditor, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        self.tracker = qt.DocumentTracker()

        self.layout = QtWidgets.QVBoxLayout(self)

        self.binder = qt.Binder(self)
        sb = self.binder
        sb.construct('trandate', 'date')
        sb.construct('tranref', 'basic')
        sb.construct('payee', 'basic')
        sb.construct('memo', 'basic')
        sb.construct('receipt', 'multiline')

        self.topgrid = QtWidgets.QGridLayout()
        self.topgrid.addWidget(qt.buddied('&Date', sb.widgets['trandate']), 0, 0)
        self.topgrid.addWidget(sb.widgets['trandate'], 0, 1)
        self.topgrid.addWidget(qt.buddied('&Reference', sb.widgets['tranref']), 0, 2)
        self.topgrid.addWidget(sb.widgets['tranref'], 0, 3)
        self.topgrid.addWidget(qt.buddied('&Payee', sb.widgets['payee']), 1, 0)
        self.topgrid.addWidget(sb.widgets['payee'], 1, 1, 1, 3)
        self.topgrid.addWidget(qt.buddied('&Memo', sb.widgets['memo']), 2, 0)
        self.topgrid.addWidget(sb.widgets['memo'], 2, 1, 1, 3)

        self.tab = QtWidgets.QTabWidget()

        self.trans_grid = widgets.EditableTableView()
        self.trans_gridmgr = qt.EditableGridManager(self.trans_grid, self)

        # first tab: transactions
        self.splitme = QtWidgets.QSplitter()
        self.splitme.addWidget(self.trans_grid)
        #self.splitme.addWidget(self.tags_table)
        self.tab.addTab(self.splitme, "&Transactions")

        # second tab:  receipt memo
        self.tab.addTab(sb.widgets['receipt'], "&Receipt")

        self.layout.addLayout(self.topgrid)
        self.layout.addWidget(self.tab)
        self.layout.addWidget(self.button_row())

        self.geo = apputils.WindowGeometry(self, position=False, tabs=[self.tab], splitters=[self.splitme])

    def bind(self, trancore):
        self.data = trancore
        self.binder.bind(self.data.tranrow, self.data.trantable.columns)

        with self.geo.grid_reset(self.trans_grid):
            columns = [
                    apputils.field('account', 'Account', type_='pyhacc_account', editable=True),
                    apputils.field('debit', 'Debit', type_='currency_usd', editable=True),
                    apputils.field('credit', 'Credit', type_='currency_usd', editable=True),
                    self.data.splittable.DataRow.model_columns['jrn_name']]
            self.trans_grid.setModel(apputils.ObjectQtModel(columns, []))
            self.trans_gridmgr.set_client_table_no_model(self.data.splittable)

    def writeback(self):
        pass

    def fields_changed(self, row, fields):
        if self.tracker.load_lockout:
            return

        for attr in fields:
            self.tracker.set_dirty(row, attr)

        if isinstance(row, self.data.splittable.DataRow):
            model = self.trans_grid.model()
            if model.is_flipper(row):
                with self.tracker.loading(reset=False):
                    newflip = self.data.splittable.flipper_row()
                model.promote_flipper(row, flipper=newflip)
                self.data.splittable.rows.append(row)
            for attr in fields:
                model.append_change_value(row, attr)


def edit_transaction(session, tranid='new'):
    dlg = TransactionEditor()

    client = session.std_client()
    backgrounder = apputils.Backgrounder(dlg)
    core = None

    def finish_load():
        nonlocal dlg, core
        payload = yield apputils.AnimateWait(dlg)
        core = TransactionCore.from_endpoint(dlg, payload)
        dlg.bind(core)

    backgrounder(finish_load, client.get, URL_BASE, tranid)

    def apply(bound):
        nonlocal client, core
        client.put(URL_BASE, core.tranrow.tid, files=core.http_files())
        return True

    dlg.applychanges = apply
    dlg.exec_()

def view_recent_transactions(parent, session):
    view = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(view)
    grid = widgets.TableView()
    grid.setSortingEnabled(True)
    grid.verticalHeader().hide()
    gridmgr = qt.GridManager(grid, view)
    layout.addWidget(grid)

    def loader():
        content = yield apputils.AnimateWait(view)
        view.table = content.main_table()

        gridmgr.set_client_table(view.table)

    backgrounder = apputils.Backgrounder(view)
    client = session.std_client()
    backgrounder(loader, client.get, URL_BASE2, date1='2019-01-01', date2='2019-12-31')

    return view


__all__ = ['edit_transaction', 'view_recent_transactions', 'TransactionCore', 'TransactionEditor']
