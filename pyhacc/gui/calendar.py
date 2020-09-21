import datetime
import uuid
from PySide2 import QtCore, QtGui, QtWidgets
import qtviews
import apputils
import apputils.models as models
import apputils.widgets as widgets
import client.qt as qt


class ChangeListener:
    def __init__(self, backgrounder, client, loadfunc, channel):
        self.client = client
        self.backgrounder = backgrounder
        self.loadfunc = loadfunc
        self.channel = channel

        self.chain_index = 0
        self.chain_key = uuid.uuid1().hex
        self.chained_listen()

    def chained_listen(self):
        kwargs = {
            "key": self.chain_key,
            "channel": self.channel,
            "index": self.chain_index,
        }
        self.backgrounder(
            self.chained_reload, self.client.get, "api/sql/changequeue", **kwargs
        )

    def chained_reload(self):
        changes = yield

        chlist = changes.main_table()
        if len(chlist.rows) > 0:
            for row in chlist.rows:
                self.chain_index = row.index

            self.loadfunc()

        self.chained_listen()


class CalendarAdaptor(QtCore.QObject):
    customContextMenuRequested = QtCore.Signal(object)
    doubleClicked = QtCore.Signal(object)

    # selectionModel
    currentRowChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()

    class _Index:
        def __init__(s, obj, attr):
            s.obj = obj
            s.attr = attr

        def isValid(s):
            return s.obj != None

        def data(s, role):
            if role == models.ObjectRole:
                return s.obj
            elif role == models.ColumnAttributeRole:
                return s.attr
            else:
                raise NotImplementedError(f"incomplete shim: role={role}")

    def __init__(self, parent, calendar, attr):
        super(CalendarAdaptor, self).__init__(parent)

        self.attr = attr
        self.calendar = calendar
        self.calendar.customContextMenuRequested.connect(
            self.customContextMenuRequested.emit
        )
        self.calendar.doubleClickCalendarEvent.connect(self.translate_double_click)

    def window(self):
        return self.parent()

    def setContextMenuPolicy(self, *args):
        self.calendar.setContextMenuPolicy(*args)

    def viewport(self, *args):
        return self.calendar.viewport()

    def addAction(self, action):
        self.calendar.addAction(action)

    def translate_double_click(self, obj):
        self.doubleClicked.emit(self._Index(obj, self.attr))

    def setModel(self, m):
        self._model = m
        self._model.rowsInserted.connect(self.reset_data)
        self._model.modelReset.connect(self.reset_data)

    def model(self):
        return self._model

    def indexAt(self, point):
        return self._Index(self.calendar.itemAt(point), self.attr)

    def selectedIndexes(self):
        index = self.calendar.currentIndex()
        objects = index.internalPointer().entryList(index)
        return [self._Index(entry, self.attr) for entry in objects]

    def selectionModel(self):
        return self

    def reset_data(self, *args):
        self.calendar.setEventList(
            self._model.rows,
            startDate=lambda x: x.trandate,
            endDate=lambda x: x.trandate,
            text=lambda x: x.memo,
            bkColor=lambda x: QtGui.QColor(0, 0, 128),
        )

    @property
    def grid(self):
        class __:
            pass

        return __()


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
            self.gridmgr.add_action("&Add Transaction", triggered=self.cmd_add_trans)
            self.gridmgr.add_action("&Copy Transaction", triggered=self.cmd_copy_trans)
            self.gridmgr.add_action("&Edit Transaction", triggered=self.cmd_edit_trans)
            self.gridmgr.add_action(
                "&Delete Transaction", triggered=self.cmd_delete_trans
            )

    def window(self):
        return self.gridmgr.grid.window()

    def cmd_add_trans(self):
        from . import transactions

        if transactions.edit_transaction(self.client.session):
            self.refresh.emit()

    def cmd_edit_trans(self, row):
        from . import transactions

        if transactions.edit_transaction(self.client.session, row.tid):
            self.refresh.emit()

    def cmd_copy_trans(self, row):
        from . import transactions

        if transactions.edit_transaction(self.client.session, row.tid, copy=True):
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


class TransactionCalendar(QtWidgets.QWidget):
    ID = "transaction-calendar"
    TITLE = "Transaction Calendar"
    URL = "api/transactions/list"

    def __init__(self, parent, session):
        super(TransactionCalendar, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.mainlayout = QtWidgets.QVBoxLayout(self)
        self.calnav = qtviews.CalendarTopNav()
        self.calendar = qtviews.CalendarView()
        self.caladapt = CalendarAdaptor(self, self.calendar, "tid")
        self.gridmgr = qt.GridManager(self.caladapt, self)

        class State:
            pass

        s = State()
        s.session = session

        self.sidebar = TransactionCommandSidebar(self, s)
        if self.sidebar != None and hasattr(self.sidebar, "init_grid_menu"):
            self.sidebar.init_grid_menu(self.gridmgr)

        self.mainlayout.addWidget(self.calnav)
        self.mainlayout.addWidget(self.calendar)

        self.change_listener = ChangeListener(
            self.backgrounder, self.client, self.load_current, "transactions"
        )

        self.calnav.relativeMove.connect(self.load_rel)
        self.calnav.absoluteMove.connect(self.load_abs)

        initdate = datetime.date.today() - datetime.timedelta(days=28)
        initdate = initdate - datetime.timedelta(days=(initdate.weekday() + 1))
        self.load_abs(initdate)

    def load_rel(self, index):
        deltas = [0, 7, 35, 365]
        delta = deltas[index] if index > 0 else -deltas[-index]
        if delta != 0:
            self.load_abs(self.current_date + datetime.timedelta(days=delta))

    def load_abs(self, date):
        self.current_date = date
        self.load_current()

    def load_current(self):
        date = self.current_date
        self.calendar.setDateRange(date, 6, dayHeight=4)
        self.backgrounder(
            self.load_tranlist,
            self.client.get,
            self.URL,
            date1=date - datetime.timedelta(days=7),
            date2=date + datetime.timedelta(days=56),
        )

    def load_tranlist(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        self.gridmgr.set_client_table(self.table)


class TransactionRecent(QtWidgets.QWidget):
    ID = "transaction-recent"
    TITLE = "Recent Transactions"
    URL = "api/transactions/list"

    def __init__(self, parent, session):
        super(TransactionRecent, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.search_edit = apputils.construct("search")
        self.setFocusProxy(self.search_edit)

        self.mainlayout = QtWidgets.QVBoxLayout(self)
        self.grid = widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)

        class State:
            pass

        s = State()
        s.session = session

        self.sidebar = TransactionCommandSidebar(self, s)
        if self.sidebar != None and hasattr(self.sidebar, "init_grid_menu"):
            self.sidebar.init_grid_menu(self.gridmgr)

        self.mainlayout.addWidget(self.search_edit)
        self.mainlayout.addWidget(self.grid)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.initial_load)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

        self.geo = apputils.WindowGeometry(
            self, position=False, size=False, grids=[self.grid]
        )

        self.change_listener = ChangeListener(
            self.backgrounder, self.client, self.initial_load, "transactions"
        )

        self.initial_load()

    def load_tranlist(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.table)

    def initial_load(self):
        kwargs = {}

        if self.search_edit.value():
            kwargs["fragment"] = self.search_edit.value()
        else:
            kwargs["date1"] = datetime.date.today() - datetime.timedelta(60)
            kwargs["date2"] = datetime.date.today() + datetime.timedelta(365)

        self.backgrounder(self.load_tranlist, self.client.get, self.URL, **kwargs)
