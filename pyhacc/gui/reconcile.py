from PySide6 import QtCore, QtWidgets
import client.qt as qt
import apputils
import apputils.widgets as widgets
from . import transactions
from . import mxc


class ReconciliationModel:
    @classmethod
    def from_endpoint(cls, controller, payload):
        self = cls()

        self.trans = payload.named_table("trans", mixin=mxc.ModelRow)
        self.trans.DataRow.controller = controller
        self.accounttable = payload.named_table("account", mixin=mxc.ModelRow)
        self.accounttable.DataRow.controller = controller
        self.account = self.accounttable.rows[0]

        return self

    def http_files(self):
        return {
            "trans": self.trans.as_http_post_file(
                inclusions=["sid", "pending", "reconciled"]
            ),
            "account": self.accounttable.as_http_post_file(
                inclusions=["id", "rec_note"]
            ),
        }

    def flip_reconciles(self):
        for t in self.trans.rows:
            if t.pending:
                t.reconciled = True
                t.pending = False

    @property
    def recbal(self):
        delta = sum([t.balance for t in self.trans.rows if t.reconciled])
        return self.account.prior_reconciled_balance + delta

    @property
    def pendbal(self):
        delta = sum([t.balance for t in self.trans.rows if t.reconciled or t.pending])
        return self.account.prior_reconciled_balance + delta

    @property
    def outbal(self):
        delta = sum([t.balance for t in self.trans.rows])
        return self.account.prior_reconciled_balance + delta


class ReconciliationWindow(QtWidgets.QDialog):
    """
    >>> app = apputils.test_app()
    >>> t = ReconciliationWindow()
    >>> t.exec_()
    1
    """

    ID = "reconciliation-window"
    TITLE = "Account Reconciliation"
    URL_BASE = "api/transactions/reconcile"

    def __init__(self, parent, state, **kwargs):
        super(ReconciliationWindow, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        self.client = state.session.std_client()
        self.backgrounder = apputils.Backgrounder(self)

        self.account = kwargs.get("account")

        self.tracker = qt.DocumentTracker()

        self.binder = qt.Binder(self)
        self.account_edit = apputils.construct("basic")

        self.recbal_edit = apputils.construct("currency_usd")
        self.pendbal_edit = apputils.construct("currency_usd")
        self.outbal_edit = apputils.construct("currency_usd")

        self.recnote_edit = self.binder.construct("rec_note", "multiline")

        self.lay1 = QtWidgets.QHBoxLayout(self)
        self.lay2 = QtWidgets.QVBoxLayout()
        self.form = QtWidgets.QFormLayout()

        self.form.addRow("Account", self.account_edit)
        self.form.addRow(qt.hline())
        self.form.addRow(QtWidgets.QLabel("Reconciliation Balances"))
        self.form.addRow("Reconciled", self.recbal_edit)
        self.form.addRow("Pending", self.pendbal_edit)
        self.form.addRow("Outstanding", self.outbal_edit)

        self.form.addRow(qt.hline())
        self.form.addRow(QtWidgets.QLabel("Reconciliation Note"))
        self.form.addRow(self.recnote_edit)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        self.buttons.addButton("Save", self.buttons.AcceptRole).clicked.connect(
            self.cmd_save
        )
        self.buttons.addButton("Reconcile", self.buttons.AcceptRole).clicked.connect(
            self.cmd_reconcile
        )
        self.buttons.addButton("Close", self.buttons.RejectRole).clicked.connect(
            self.reject
        )

        self.lay1.addLayout(self.lay2)
        self.lay2.addLayout(self.form)
        self.lay2.addWidget(self.buttons)

        self.trans_grid = widgets.EditableTableView()
        self.trans_grid.setSortingEnabled(True)
        self.trans_gridmgr = qt.EditableGridManager(
            self.trans_grid, self, fixed_rowset=True
        )

        self.lay1.addWidget(self.trans_grid)

        self.lay1.setStretch(1, 5)

        self.sidebar = transactions.TransactionCommandSidebar(self, state)
        if self.sidebar != None and hasattr(self.sidebar, "init_grid_menu"):
            self.sidebar.init_grid_menu(self.trans_gridmgr)

        self.geo = apputils.WindowGeometry(self, grids=[self.trans_grid])

    def cmd_save(self):
        if self.tracker.window_new_document(self, self.save):
            self.refresh()

    def cmd_reconcile(self):
        self.data.flip_reconciles()

        if self.tracker.window_new_document(self, self.save):
            self.refresh()

    def reject(self):
        if self.tracker.window_close(self, self.save):
            super(ReconciliationWindow, self).reject()

    def save(self):
        with apputils.animator(self) as p:
            p.background(self.client.put, self.URL_BASE, files=self.data.http_files())

    def refresh(self):
        self.backgrounder(
            self.load, self.client.get, self.URL_BASE, account=self.account
        )

    def load(self):
        payload = yield apputils.AnimateWait(self)

        with self.tracker.loading():
            self.data = ReconciliationModel.from_endpoint(self, payload)

            # load form
            self.account_edit.setValue(self.data.account.acc_name)
            self.recbal_edit.setValue(self.data.recbal)
            self.pendbal_edit.setValue(self.data.pendbal)
            self.outbal_edit.setValue(self.data.outbal)
            self.binder.bind(self.data.account, self.data.accounttable.columns)

            # load grid
            with self.geo.grid_reset(self.trans_grid):
                columns = []
                for attr, col in self.data.trans.DataRow.model_columns.items():
                    if attr in ("pending", "reconciled"):
                        col.mutate(editable=True)
                    columns.append(col)
                self.trans_grid.setModel(apputils.ObjectQtModel(columns, []))
                self.trans_gridmgr.set_client_table_no_model(self.data.trans)

                self.tracker.set_mayor_list([self.binder, self.trans_grid])

    def fields_changed(self, row, fields):
        if self.tracker.load_lockout:
            return

        if "pending" in fields or "reconciled" in fields:
            self.recbal_edit.setValue(self.data.recbal)
            self.pendbal_edit.setValue(self.data.pendbal)

        for attr in fields:
            self.tracker.set_dirty(row, attr)

        if isinstance(row, self.data.trans.DataRow):
            model = self.trans_grid.model()
            for attr in fields:
                model.append_change_value(row, attr)
