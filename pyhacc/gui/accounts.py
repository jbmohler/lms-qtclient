import datetime
from PySide6 import QtCore, QtWidgets
import client.qt as qt
import apputils
import apputils.widgets
import rtlib.boa
from . import widgets
from . import transactions

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

        self.view_select = apputils.construct("options")
        self.view_select.applyValue.connect(self.on_view_select)
        self.layout.addWidget(self.view_select)

        self.topstack = QtWidgets.QStackedWidget()

        self.account_view = QtWidgets.QTextBrowser()
        self.account_view.setStyleSheet("QTextEdit { font-size: 14px }")
        self.account_view.setOpenLinks(False)
        self.account_view.anchorClicked.connect(self.action_triggered)

        self.contact_sidebar = qt.plugpoint.get_plugin_sidebar("persona_general")

        self.topstack.addWidget(self.account_view)
        self.topstack.addWidget(self.contact_sidebar)
        self.layout.addWidget(self.topstack)

        self.grid = apputils.widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.gridmgr = qt.GridManager(self.grid, self)

        self.layout.addWidget(self.grid)

        self.tran_sidebar = transactions.TransactionCommandSidebar(self, state)
        if self.tran_sidebar != None and hasattr(self.tran_sidebar, "init_grid_menu"):
            self.tran_sidebar.init_grid_menu(self.gridmgr)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

    def highlight(self, row):
        if row == None:
            return

        self.contacts_table = None

        self.refresh_account(row.id)
        self.refresh_transactions(row.id)

    def action_triggered(self, url):
        pass

    def prepare_view_select(self):
        row = self.account_table.rows[0]

        options = [(f"Account: {row.acc_name}", f"account:{row.id}")]

        if self.contacts_table is not None:
            for persona in self.contacts_table.rows:
                vp = (f"Contact: {persona.entity_name}", f"contact:{persona.id}")
                options.append(vp)

        self.view_select.set_options(options)

        self.on_view_select()

    def on_view_select(self):
        value = self.view_select.value()

        if value is None:
            vtype, vid = "account", None
        else:
            vtype, vid = value.split(":")

        if vtype == "account":
            self.topstack.setCurrentIndex(0)
        elif vtype == "contact":
            xx = rtlib.boa.inline_object(id=vid)
            self.contact_sidebar.highlight(xx)
            self.topstack.setCurrentIndex(1)

    def refresh_account(self, account_id):
        self.backgrounder(
            self.load_account,
            self.client.get,
            "api/account/{}",
            account_id,
        )

    def load_account(self):
        results = yield apputils.AnimateWait(self.topstack)
        self.account_table = results.main_table()

        row = self.account_table.rows[0]
        if row.acc_note:
            acc_note = row.acc_note.replace("\n", "<br />")
        else:
            acc_note = ""

        self.account_view.setHtml(
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

        self.prepare_view_select()

        # trigger a load for the contacts
        if row.contact_keywords:
            self.refresh_contacts(row.contact_keywords)

    def refresh_contacts(self, keywords):
        # beware the cross module reach
        self.backgrounder(
            self.load_contacts, self.client.get, "api/personas/list", frag=keywords
        )

    def load_contacts(self):
        results = yield apputils.AnimateWait(self.grid)

        self.contacts_table = results.main_table()

        self.prepare_view_select()

    def refresh_transactions(self, account_id):
        today = datetime.date.today()
        d1 = today + datetime.timedelta(days=-365)
        d2 = today + datetime.timedelta(days=10 * 365)

        self.backgrounder(
            self.load_transactions,
            self.client.get,
            "api/transactions/tran-detail",
            date1=d1.isoformat(),
            date2=d2.isoformat(),
            account=account_id,
        )

    def load_transactions(self):
        results = yield apputils.AnimateWait(self.grid)

        self.transaction_table = results.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.transaction_table)


def edit_account(session, acntid="new", parent=None):
    dlg = qt.FormEntryDialog("PyHacc Account", parent=parent)

    dlg.add_form_row("acc_name", "Account", "basic")
    dlg.add_form_row("description", "Description", "basic")
    dlg.add_form_row("journal_id", "Journal", "pyhacc_journal.id")
    dlg.add_form_row("type_id", "Type", "pyhacc_accounttype.id")
    dlg.add_form_row("retearn_id", "Retained Earnings", "pyhacc_account.id")
    dlg.add_form_row("acc_note", "Account Note", "multiline")
    dlg.add_form_row("rec_note", "Reconciliation Note", "multiline")
    dlg.add_form_row("contact_keywords", "Contact Keywords", "basic")

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


class AccountCommandSidebar(QtCore.QObject):
    SRC_INSTANCE_URL = "api/account/{}"
    refresh = QtCore.Signal()

    def __init__(self, parent, state):
        super(AccountCommandSidebar, self).__init__(parent)
        self.client = state.session.std_client()
        self.added = False

    def init_grid_menu(self, gridmgr):
        self.gridmgr = gridmgr

        if not self.added:
            self.added = True
            self.gridmgr.add_action(
                "&Edit Account",
                triggered=self.cmd_edit_account,
                role_group="add_remove",
                default=True,
                shortcut="Ctrl+E",
                shortcut_parent=gridmgr.parent(),
            )
            self.gridmgr.add_action(
                "&New Account",
                triggered=self.cmd_add_account,
                role_group="add_remove",
                shortcut="Ctrl+N",
                shortcut_parent=gridmgr.parent(),
            )
            self.gridmgr.add_action(
                "&Delete Account",
                triggered=self.cmd_delete_account,
                role_group="add_remove",
            )

    def window(self):
        return self.gridmgr.grid.window()

    def cmd_add_account(self):
        if edit_account(self.client.session, parent=self.window()):
            self.refresh.emit()

    def cmd_edit_account(self, row):
        if edit_account(self.client.session, acntid=row.id, parent=self.window()):
            self.refresh.emit()

    def cmd_delete_account(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f"Are you sure that you wish to delete the account {row.account} ({row.description})?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.id)
                self.refresh.emit()
            except:
                qt.exception_message(
                    self.window(), "The transaction could not be deleted."
                )


class AccountsList(QtWidgets.QWidget):
    ID = "accounts-list"
    TITLE = "Accounts List"
    URL = "api/accounts/list"

    def __init__(self, parent, state):
        super(AccountsList, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = state.session.std_client()

        self.mainlayout = QtWidgets.QVBoxLayout(self)

        self.journal_edit = apputils.construct("pyhacc_journal.id", all_option=True)
        self.atype_edit = apputils.construct("pyhacc_accounttype.id", all_option=True)

        self.prompts = QtWidgets.QFormLayout()
        self.prompts.addRow("Journal", self.journal_edit)
        self.prompts.addRow("Account Type", self.atype_edit)

        self.sublay = qt.RevealedSplitter(QtCore.Qt.Horizontal)

        self.grid = apputils.widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)
        self.sublay.addWidget(self.grid)

        self.sidebar2 = AccountCommandSidebar(self, state)
        if self.sidebar2 != None and hasattr(self.sidebar2, "init_grid_menu"):
            self.sidebar2.init_grid_menu(self.gridmgr)

        self.sidebar = AccountSidebar(self, state)
        self.sublay.addWidget(self.sidebar)

        self.mainlayout.addLayout(self.prompts)
        self.mainlayout.addWidget(self.sublay, stretch=4)

        self.preview_timer = qt.StdActionPause()
        self.preview_timer.timeout.connect(
            lambda: self.sidebar.highlight(self.gridmgr.selected_row())
        )
        self.gridmgr.current_row_update.connect(self.preview_timer.ui_start)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.initial_load)
        self.journal_edit.applyValue.connect(self.load_timer.ui_start)
        self.atype_edit.applyValue.connect(self.load_timer.ui_start)

        self.geo = apputils.WindowGeometry(
            self, position=False, size=False, grids=[self.grid]
        )

        widgets.verify_settings_load(
            self, self.client, [self.journal_edit, self.atype_edit]
        )

        self.initial_load()

    def load_mainlist(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.table)

    def initial_load(self):
        kwargs = {}
        kwargs["acctype"] = self.atype_edit.value()
        kwargs["journal"] = self.journal_edit.value()

        self.backgrounder(self.load_mainlist, self.client.get, self.URL, **kwargs)


__all__ = ["edit_account", "AccountsList"]
