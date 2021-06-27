import datetime
from PySide6 import QtCore, QtGui, QtWidgets
import client.qt as qt
import apputils
import apputils.widgets as widgets
from . import widgets as pywid
from . import mxc

URL_BASE = "api/transaction/{}"


def null0(v):
    return v if v != None else 0.0


class SplitsTable(mxc.ModelRow):
    def _rtlib_init_(self):
        if self.sum == None:
            self._debit = None
            self._credit = None
        else:
            self._debit = self.sum if self.sum > 0 else None
            self._credit = -self.sum if self.sum < 0 else None

    def _init_flipper_(self):
        self._debit = None
        self._credit = None

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
        self.sum = null0(self._debit) - null0(self._credit)

    @property
    def credit(self):
        try:
            return self._credit
        except:
            return None

    @credit.setter
    def credit(self, v):
        self._credit = v
        self.sum = null0(self._debit) - null0(self._credit)


class TransactionCore:
    def __init__(self):
        pass

    @classmethod
    def from_endpoint(cls, controller, content):
        self = cls()
        self.trantable = content.named_table("trans", mixin=mxc.ModelRow)
        self.trantable.DataRow.controller = controller
        self.tranrow = self.trantable.rows[0]
        self.splittable = content.named_table("splits", mixin=SplitsTable)
        self.splittable.DataRow.controller = controller
        return self

    def cmd_balance(self, split):
        if split == None:
            return
        balance = 0
        for row in self.splittable.rows:
            if row is not split:
                balance -= row.sum
        kwargs = {
            "debit": balance if balance >= 0.0 else None,
            "credit": -balance if balance < 0.0 else None,
        }
        split.multiset(**kwargs)

    def cmd_reverse(self):
        for row in self.splittable.rows:
            kwargs = {
                "debit": row.credit,
                "credit": row.debit,
            }
            row.multiset(**kwargs)

    def http_files(self):
        return {
            "trans": self.trantable.as_http_post_file(),
            "splits": self.splittable.as_http_post_file(),
        }

    def ascii_repr(self):
        lines = []
        if self.tranrow.trandate is not None:
            lines.append(f"Date:  {self.tranrow.trandate}")
        if self.tranrow.tranref not in [None, ""]:
            lines.append(f"Reference:  {self.tranrow.tranref}")
        if self.tranrow.payee not in [None, ""]:
            lines.append(f"Payee:  {self.tranrow.payee}")
        if self.tranrow.memo not in [None, ""]:
            lines.append(f"Memo:  {self.tranrow.memo}")
        lines.append("-" * (20 + 1 + 12 + 1 + 12))
        for x in self.splittable.rows:
            debstr = " " * 12 if x.debit == None else f"{x.debit:12.2f}"
            credstr = " " * 12 if x.credit == None else f"{x.credit:12.2f}"
            lines.append(f"{x.account.acc_name:<20} {debstr} {credstr}")
        lines.append("-" * (20 + 1 + 12 + 1 + 12))

        return "\n".join(lines)


class TransactionEditor(qt.ObjectDialog):
    """
    >>> app = apputils.test_app()
    >>> t = TransactionEditor()
    >>> t.exec_()
    1
    """

    ID = "transaction-editor"
    TITLE = "PyHacc Transaction"

    def __init__(self, parent=None):
        super(TransactionEditor, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        # NOTE:  no save callback, this may be useless?
        self.tracker = qt.DocumentTracker(self, None)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.binder = qt.Binder(self)
        sb = self.binder
        sb.construct("trandate", "date")
        sb.construct("tranref", "basic")
        sb.construct("payee", "basic")
        sb.construct("memo", "basic")
        sb.construct("receipt", "richtext")

        self.topgrid = QtWidgets.QGridLayout()
        self.topgrid.addWidget(qt.buddied("&Date", sb.widgets["trandate"]), 0, 0)
        self.topgrid.addWidget(sb.widgets["trandate"], 0, 1)
        self.topgrid.addWidget(qt.buddied("&Reference", sb.widgets["tranref"]), 0, 2)
        self.topgrid.addWidget(sb.widgets["tranref"], 0, 3)
        self.topgrid.addWidget(qt.buddied("&Payee", sb.widgets["payee"]), 1, 0)
        self.topgrid.addWidget(sb.widgets["payee"], 1, 1, 1, 3)
        self.topgrid.addWidget(qt.buddied("&Memo", sb.widgets["memo"]), 2, 0)
        self.topgrid.addWidget(sb.widgets["memo"], 2, 1, 1, 3)

        self.tab = QtWidgets.QTabWidget()

        self.trans_grid = widgets.EditableTableView()
        self.trans_gridmgr = qt.EditableGridManager(self.trans_grid, self)

        # first tab: transactions
        self.splitme = QtWidgets.QSplitter()
        self.splitme.addWidget(self.trans_grid)
        # self.splitme.addWidget(self.tags_table)
        self.tab.addTab(self.splitme, "&Transactions")

        # second tab:  receipt memo
        self.tab.addTab(sb.widgets["receipt"], "&Receipt")

        self.tran_status_label = QtWidgets.QLabel()

        self.layout.addWidget(self.tran_status_label)
        self.layout.addLayout(self.topgrid)
        self.layout.addWidget(self.tab)
        self.layout.addWidget(self.button_row())

        self.action_balance = QtGui.QAction("&Balance on Current Line", self)
        self.action_balance.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_B)
        self.action_balance.triggered.connect(
            lambda: self.data.cmd_balance(self.trans_gridmgr.selected_row())
        )
        self.addAction(self.action_balance)

        self.action_reverse = QtGui.QAction("&Reverse Transaction", self)
        self.action_reverse.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_R)
        self.action_reverse.triggered.connect(lambda: self.data.cmd_reverse())
        self.addAction(self.action_reverse)

        self.action_copyplain = QtGui.QAction("Copy as Plain Text", self)
        self.action_copyplain.triggered.connect(self.cmd_copyplain)
        self.addAction(self.action_copyplain)

        btns = self.button_row()
        btn_menu = btns.addButton("&More", btns.ActionRole)
        self.menu_more = QtWidgets.QMenu()
        self.menu_more.addAction(self.action_balance)
        self.menu_more.addAction(self.action_reverse)
        self.menu_more.addAction(self.action_copyplain)
        btn_menu.setMenu(self.menu_more)

        self.geo = apputils.WindowGeometry(
            self, position=False, tabs=[self.tab], splitters=[self.splitme]
        )

    def bind(self, trancore):
        self.data = trancore
        self.binder.bind(self.data.tranrow, self.data.trantable.columns)

        self.tran_status_label.setStyleSheet(
            f"QLabel {{ color : {self.data.tranrow.tran_status_color}; }}"
        )
        self.tran_status_label.setText(self.data.tranrow.tran_status)

        with self.geo.grid_reset(self.trans_grid):
            columns = [
                apputils.field(
                    "account", "Account", type_="pyhacc_account", editable=True
                ),
                apputils.field("debit", "Debit", type_="currency_usd", editable=True),
                apputils.field("credit", "Credit", type_="currency_usd", editable=True),
                self.data.splittable.DataRow.model_columns["jrn_name"],
            ]
            self.trans_grid.setModel(apputils.ObjectQtModel(columns, []))
            self.trans_gridmgr.set_client_table_no_model(self.data.splittable)

    def cmd_copyplain(self):
        QtWidgets.QApplication.clipboard().setText(self.data.ascii_repr())

    def writeback(self):
        pass

    def preset_group(self, obj, kwargs):
        pass

    def fields_changed(self, row, fields):
        if self.tracker.load_lockout:
            return

        for attr in fields:
            self.tracker.set_dirty(row, attr)

        if isinstance(row, self.data.splittable.DataRow):
            # read the journal
            if "account_id" in fields:
                payload = self.client.get("api/account/{}", row.account_id)
                row.jrn_name = payload.main_table().rows[0].jrn_name

            # update the view
            model = self.trans_grid.model()
            if model.is_flipper(row):
                with self.tracker.loading(reset=False):
                    newflip = self.data.splittable.flipper_row()
                model.promote_flipper(row, flipper=newflip)
                self.data.splittable.rows.append(row)
            for attr in fields:
                model.append_change_value(row, attr)
            model.object_changed(row)


def edit_transaction(session, tranid="new", copy=False):
    dlg = TransactionEditor()

    client = session.std_client()
    dlg.client = client
    backgrounder = apputils.Backgrounder(dlg)
    core = None

    def finish_load():
        nonlocal dlg, core
        payload = yield apputils.AnimateWait(dlg)
        core = TransactionCore.from_endpoint(dlg, payload)
        dlg.bind(core)

    if copy:
        assert tranid != "new"
        url = URL_BASE + "/copy"
    else:
        url = URL_BASE

    backgrounder(finish_load, client.get, url, tranid)

    def apply(bound):
        nonlocal client, core
        client.put(URL_BASE, core.tranrow.tid, files=core.http_files())
        return True

    dlg.applychanges = apply
    dlg.exec_()


class TransactionCommandSidebar(QtCore.QObject):
    SRC_INSTANCE_URL = "api/transaction/{}"
    refresh = QtCore.Signal()

    def __init__(self, parent, state):
        super(TransactionCommandSidebar, self).__init__(parent)
        self.client = state.session.std_client()
        self.added = False

    def init_grid_menu(self, gridmgr):
        self.gridmgr = gridmgr

        if not self.added:
            self.added = True
            self.gridmgr.add_action(
                "&Edit Transaction",
                triggered=self.cmd_edit_trans,
                role_group="add_remove",
                default=True,
            )
            self.gridmgr.add_action(
                "&Copy Transaction",
                triggered=self.cmd_copy_trans,
                role_group="add_remove",
            )
            self.gridmgr.add_action(
                "&New Transaction",
                triggered=self.cmd_add_trans,
                role_group="add_remove",
            )
            self.gridmgr.add_action(
                "&Delete Transaction",
                triggered=self.cmd_delete_trans,
                role_group="add_remove",
            )

    def window(self):
        return self.gridmgr.grid.window()

    def cmd_add_trans(self):
        if edit_transaction(self.client.session):
            self.refresh.emit()

    def cmd_edit_trans(self, row):
        if edit_transaction(self.client.session, row.tid):
            self.refresh.emit()

    def cmd_copy_trans(self, row):
        if edit_transaction(self.client.session, row.tid, copy=True):
            self.refresh.emit()

    def cmd_delete_trans(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f"Are you sure that you wish to delete the transaction for {row.payee} and memo {row.memo}?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.tid)
                self.refresh.emit()
            except:
                qt.exception_message(
                    self.window(), "The transaction could not be deleted."
                )


__all__ = [
    "edit_transaction",
    "TransactionCore",
    "TransactionEditor",
    "TransactionCommandSidebar",
]
