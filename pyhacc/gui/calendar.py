import datetime
from PySide2 import QtCore, QtGui, QtWidgets
import qtviews
import apputils

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

        self.lay.addWidget(self.calnav)
        self.lay.addWidget(self.calendar)

        self.calnav.relativeMove.connect(self.load_rel)
        self.calnav.absoluteMove.connect(self.load_abs)

        initdate = datetime.date.today() - datetime.timedelta(days=38)
        self.load_abs(initdate)

    def load_rel(self):
        deltas = [0, 7, 35, 365]
        delta = deltas[index] if index > 0 else -deltas[-index]
        if delta != 0:
            self.load_abs(nav.current_date + datetime.timedelta(delta))

    def load_abs(self, date):
        self.current_date = date
        self.calendar.setDateRange(date, 6)
        self.backgrounder(self.load_entry_data, self.client.get, 'api/transactions/recent-header', date1=date-datetime.timedelta(days=7), date2=date+datetime.timedelta(days=56))

    def load_entry_data(self):
        content = yield apputils.AnimateWait(self)

        self.table = content.main_table()

        self.calendar.setEventList(self.table.rows, 
            startDate = lambda x: x.trandate,
            endDate = lambda x: x.trandate,
            text = lambda x: x.memo,
            bkColor = lambda x: QtGui.QColor(0, 0, 128))
