import xml.dom.minidom as xml
from PySide6 import QtWidgets, QtCore
import client.qt as qt
import apputils

URL_BASE = "api/roscoe"

"""
Twilio params:

    ('SmsSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('FromState', 'PA')
    ('MessageSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('ToZip', '19406')
    ('FromCity', 'NORRISTOWN')
    ('ToCity', 'NORRISTOWN')
    ('Body', 'Have a good day')
    ('ToState', 'PA')
    ('AccountSid', 'AC89a4ccde189dc41f0df85ac6fe74ecdf')
    ('ToCountry', 'US')
    ('FromZip', '19403')
    ('NumMedia', '0')
    ('To', '+14843334444')
    ('From', '+14845556666')
    ('SmsStatus', 'received')
    ('SmsMessageSid', 'SMa9f871c6f183163a54199a5259bfb994')
    ('FromCountry', 'US')
    ('MessagingServiceSid', 'MG7ff59c61b16993c055c73c185357f177')
    ('ApiVersion', '2010-04-01')
    ('NumSegments', '1')
"""

TEST_PHONES = ["+11234567890", "+14843334444", "+14845556666"]


class TwilioParams:
    def __init__(self):
        pass

    def get_data(self):
        return {"Body": self.Body, "From": self.From}


def test_roscoe(session):
    dlg = qt.FormEntryDialog("PyHacc Roscoe Test")

    dlg.add_form_row("Body", "Message", "basic")
    dlg.add_form_row(
        "From", "Source phone", "options", options=[(p, p) for p in TEST_PHONES]
    )

    def apply(bound):
        nonlocal session, dlg
        client = session.raw_client()
        payload = client.post(URL_BASE, data=bound.get_data())
        root = xml.parseString(payload)
        xx = root.toprettyxml()
        apputils.information(dlg, f"TwiML:\n\n{xx}", richtext=False)

    obj = TwilioParams()
    obj.Body = ""
    obj.From = TEST_PHONES[1]

    dlg.bind(obj)
    dlg.applychanges = apply

    dlg.exec_()


class PendingRoscoe(QtWidgets.QWidget):
    TITLE = "Pending Roscoe"
    ID = "roscoe-pending"
    URL = "api/roscoe/unprocessed"

    def __init__(self, parent, state):
        super(PendingRoscoe, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = state.session.std_client()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.grid = apputils.widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)
        self.layout.addWidget(self.grid)

        self.gridmgr.add_action("&Clear Queue...", triggered=self.cmd_clear_queue)

        self.geo = apputils.WindowGeometry(
            self, position=False, size=False, grids=[self.grid]
        )

        self.initial_load()

    def load_mainlist(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.table)

    def initial_load(self):
        kwargs = {}

        self.backgrounder(self.load_mainlist, self.client.get, self.URL, **kwargs)

    def cmd_clear_queue(self):
        if "Yes" == apputils.message(
            self.window(),
            "This will clear the list.  Are you sure you wish to continue?",
            buttons=["Yes", "No"],
        ):
            with apputils.animator(self) as p:
                p.background(self.client.put, "api/roscoe/mark-processed")
            self.initial_load()


def setup_timer(session, parent):
    def check_roscoe():
        client = session.std_client()
        payload = client.get(PendingRoscoe.URL)
        table = payload.main_table()

        if len(table.rows):
            parent.handle_url("pyhacc:roscoe/dock")

    # TODO setup a long poll rather than timer based
    timer = QtCore.QTimer(parent)
    timer.setInterval(60 * 1000)

    timer.timeout.connect(check_roscoe)
    timer.start()

    return timer
