import datetime
from PySide2 import QtCore, QtGui, QtWidgets
import qtviews
import apputils
import apputils.models as models
import apputils.widgets as widgets
import client.qt as qt


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

        self.mainlayout.addWidget(self.calnav)
        self.mainlayout.addWidget(self.calendar)

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
    TITLE = "Transaction Recent"
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

        self.mainlayout.addWidget(self.search_edit)
        self.mainlayout.addWidget(self.grid)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.initial_load)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

        self.geo = apputils.WindowGeometry(
            self, position=False, size=False, grids=[self.grid]
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
