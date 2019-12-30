import datetime
from PySide2 import QtCore, QtGui, QtWidgets
import qtviews
import apputils
import apputils.models as models
from client.qt import gridmgr

class CalendarAdaptor(QtCore.QObject):
    customContextMenuRequested = QtCore.Signal(object)
    doubleClicked = QtCore.Signal()

    # selectionModel
    currentRowChanged = QtCore.Signal()
    selectionChanged = QtCore.Signal()

    class _Index:
        def __init__(s, obj):
            s.obj = obj
        def isValid(s):
            return s.obj != None
        def data(s, role):
            if role != models.ObjectRole:
                raise NotImplementedError('incomplete shim')
            return s.obj

    def __init__(self, parent, calendar):
        super(CalendarAdaptor, self).__init__(parent)

        self.calendar = calendar
        self.calendar.customContextMenuRequested.connect(self.customContextMenuRequested.emit)
        self.calendar.doubleClicked.connect(self.doubleClicked.emit)

    def setContextMenuPolicy(self, *args):
        self.calendar.setContextMenuPolicy(*args)

    def viewport(self, *args):
        return self.calendar.viewport()

    def addAction(self, action):
        self.calendar.addAction(action)

    def setModel(self, m):
        self._model = m
        self._model.rowsInserted.connect(self.reset_data)
        self._model.modelReset.connect(self.reset_data)

    def model(self):
        return self._model

    def indexAt(self, point):
        return self._Index(self.calendar.itemAt(point))

    def selectedIndexes(self):
        index = self.calendar.currentIndex()
        objects = index.internalPointer().entryList(index)
        return [self._Index(entry) for entry in objects]

    def selectionModel(self):
        return self

    def reset_data(self, *args):
        self.calendar.setEventList(self._model.rows, 
            startDate = lambda x: x.trandate,
            endDate = lambda x: x.trandate,
            text = lambda x: x.memo,
            bkColor = lambda x: QtGui.QColor(0, 0, 128))

    @property
    def grid(self):
        class __:
            pass
        return __()

class TransactionCalendar(QtWidgets.QWidget):
    ID = 'transaction-calendar'

    def __init__(self, parent, session):
        super(TransactionCalendar, self).__init__(parent)

        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.lay = QtWidgets.QVBoxLayout(self)
        self.calnav = qtviews.CalendarTopNav()
        self.calendar = qtviews.CalendarView()
        self.caladapt = CalendarAdaptor(self, self.calendar)
        self.gridmgr = gridmgr.GridManager(self.caladapt, self)

        self.lay.addWidget(self.calnav)
        self.lay.addWidget(self.calendar)

        self.calnav.relativeMove.connect(self.load_rel)
        self.calnav.absoluteMove.connect(self.load_abs)

        initdate = datetime.date.today() - datetime.timedelta(days=28)
        initdate = initdate - datetime.timedelta(days=(initdate.weekday()+1))
        self.load_abs(initdate)

    def load_rel(self, index):
        deltas = [0, 7, 35, 365]
        delta = deltas[index] if index > 0 else -deltas[-index]
        if delta != 0:
            self.load_abs(self.current_date + datetime.timedelta(days=delta))

    def load_abs(self, date):
        self.current_date = date
        self.calendar.setDateRange(date, 6, dayHeight=4)
        self.backgrounder(self.load_entry_data, self.client.get,
                'api/transactions/list', date1=date-datetime.timedelta(days=7), date2=date+datetime.timedelta(days=56))

    def load_entry_data(self):
        content = yield apputils.AnimateWait(self)

        self.table = content.main_table()

        self.gridmgr.set_client_table(self.table)
