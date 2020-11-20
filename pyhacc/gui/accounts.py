from PySide2 import QtWidgets
import client.qt as qt
import apputils
import apputils.widgets
from . import widgets

URL_BASE = "api/account/{}"


class AccountSidebar(QtWidgets.QWidget):
    TITLE = "Account"
    ID = "account-preview"

    def __init__(self, parent, state):
        super(AccountSidebar, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = state.session.std_client()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = QtWidgets.QTextBrowser()
        self.view.setStyleSheet("QTextEdit { font-size: 14px }")
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.action_triggered)
        self.layout.addWidget(self.view)

        self.grid = apputils.widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.gridmgr = qt.GridManager(self.grid, self)

        self.layout.addWidget(self.grid)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

    def highlight(self, row):
        self.refresh_account(row.id)
        self.refresh_transactions(row.id)

    def action_triggered(self, url):
        pass

    def refresh_account(self, account_id):
        self.backgrounder(
            self.load_account,
            self.client.get,
            "api/account/{}",
            account_id,
        )

    def load_account(self):
        results = yield apputils.AnimateWait(self.view)
        self.account_table = results.main_table()

        row = self.account_table.rows[0]
        if row.acc_note:
            acc_note = row.acc_note.replace("\n", "<br />")
        else:
            acc_note = ""

        self.view.setHtml(
            f"""
<html>
<body>
<b>Account: </b>{row.acc_name}<br />
<b>Journal: </b>{row.jrn_name}<br />
<b>Description: </b>{row.description}<br />
<b>Note: </b><br />{acc_note}<br />
</body>
</html>
"""
        )

    def refresh_transactions(self, account_id):
        self.backgrounder(
            self.load_transactions,
            self.client.get,
            "api/transactions/tran-detail",
            date1="2020-01-01",
            date2="2020-12-31",
            account=account_id,
        )

    def load_transactions(self):
        results = yield apputils.AnimateWait(self.grid)

        self.transaction_table = results.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.transaction_table)


def edit_account(session, acntid="new"):
    dlg = qt.FormEntryDialog("PyHacc Account")

    dlg.add_form_row("acc_name", "Account", "basic")
    dlg.add_form_row("description", "Description", "basic")
    dlg.add_form_row("type_id", "Type", "pyhacc_accounttype.id")
    dlg.add_form_row("journal_id", "Journal", "pyhacc_journal.id")
    dlg.add_form_row("acc_note", "Account Note", "multiline")
    dlg.add_form_row("rec_note", "Reconciliation Note", "multiline")

    client = session.std_client()

    payload = client.get(URL_BASE, acntid)
    table = payload.main_table()

    def apply(bound):
        nonlocal client, table
        client.put(
            URL_BASE,
            bound.id,
            files={
                "account": table.as_http_post_file(
                    exclusions=["atype_name", "jrn_name"]
                )
            },
        )
        return True

    widgets.verify_settings_load(dlg, client, dlg.binder)

    dlg.bind(table.rows[0])
    dlg.applychanges = apply
    dlg.exec_()


__all__ = ["edit_account"]
