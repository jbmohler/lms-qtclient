from .widgets import *


from . import accounts
from . import accounttypes
from . import journals
from . import tranreports
from . import roscoe
from . import monthly
from . import transactions
from . import calendar
from . import reconcile


class AccountingExtensions:
    def show_link_parented(self, state, parent, url):
        if url.scheme() != "pyhacc":
            return False

        if url.path() == "accounts/new":
            accounts.edit_account(state.session, "new")
        elif url.path() == "accounts":
            accounts.edit_account(state.session, url.parameters()["key"])
        elif url.path() == "accounts/list":
            view = accounts.AccountsList(parent, state)
            parent.adopt_tab(view, view.ID, view.TITLE)
        elif url.path() == "journals/new":
            journals.edit_journal(state.session, "new")
        elif url.path() == "journals":
            journals.edit_journal(state.session, url.parameters()["key"])
        elif url.path() == "accounttypes/new":
            accounttypes.edit_account_type(state.session, "new")
        elif url.path() == "accounttypes":
            accounttypes.edit_account_type(state.session, url.parameters()["key"])
        elif url.path() == "reconcile":
            w = reconcile.ReconciliationWindow(None, state, **url.parameters())
            w.show()
            w.refresh()
        elif url.path() == "transactions/new":
            transactions.edit_transaction(state.session, "new")
        elif url.path() == "transactions":
            transactions.edit_transaction(state.session, url.parameters()["key"])
        elif url.path() == "transactions/recent":
            existing = parent.foreground_tab(calendar.TransactionRecent.ID)
            if existing:
                existing.focus_search()
                return True
            view = calendar.TransactionRecent(parent, state)
            parent.adopt_tab(view, view.ID, view.TITLE)
        elif url.path() == "transactions/calendar":
            if parent.foreground_tab(calendar.TransactionCalendar.ID):
                return True
            view = calendar.TransactionCalendar(parent, state)
            parent.adopt_tab(view, view.ID, view.TITLE)
        elif url.path() == "reporting/monthly-status":
            win = monthly.Exporter(state)
            win.show()
        elif url.path() == "roscoe/client-test":
            roscoe.test_roscoe(state.session)
        elif url.path() == "roscoe/dock":
            existing = parent.foreground_tab(roscoe.PendingRoscoe.ID)
            if existing:
                # existing.focus_search()
                return True
            view = roscoe.PendingRoscoe(parent, state)
            parent.adopt_tab(view, view.ID, view.TITLE, addto="dock:bottom")
        else:
            return False
        return True

    def get_menus(self):
        account_menu_schematic = [
            (
                "ClientURLMenuItem",
                ("&Account List", "pyhacc:accounts/list", "get_api_accounts_list"),
            ),
            (
                "ClientURLMenuItem",
                ("New &Journal", "pyhacc:journals/new", "get_api_journal_new"),
            ),
            (
                "ClientURLMenuItem",
                (
                    "New Account &Type",
                    "pyhacc:accounttypes/new",
                    "get_api_accounttype_new",
                ),
            ),
            ("SeparatorMenuItem", ()),
            (
                "ClientURLMenuItem",
                (
                    "Roscoe &Pending Dock",
                    "pyhacc:roscoe/dock",
                    "get_api_roscoe_unprocessed",
                ),
            ),
            (
                "ClientURLMenuItem",
                ("Test &Roscoe", "pyhacc:roscoe/client-test", "post_api_roscoe"),
            ),
        ]
        yield ("&Accounts", account_menu_schematic)

        tran_menu_schematic = [
            (
                "ClientURLMenuItem",
                (
                    "New &Transaction",
                    "pyhacc:transactions/new",
                    "get_api_transaction_new",
                    "Ctrl+N",
                ),
            ),
            (
                "ClientURLMenuItem",
                (
                    "&Recent Transactions",
                    "pyhacc:transactions/recent",
                    "get_api_transactions_list",
                    "Ctrl+R",
                ),
            ),
            (
                "ClientURLMenuItem",
                (
                    "&Calendar Transactions",
                    "pyhacc:transactions/calendar",
                    "api_transactions_recent_header",
                ),
            ),
            ("SeparatorMenuItem", ()),
            (
                "ClientURLMenuItem",
                (
                    "Monthly &Status...",
                    "pyhacc:reporting/monthly-status",
                    "api_gledger_balance_sheet",
                ),
            ),
        ]
        yield ("&Transactions", tran_menu_schematic)

    def load_sidebar(self, state, name):
        if name == "account_general":
            return accounts.AccountSidebar(None, state)

    def report_formats(self, state, name):
        if name == "gl_summarize_by_type":
            return tranreports.AccountTypeGrouped()
        if name == "gl_summarize_total":
            return tranreports.FullGrouped()
