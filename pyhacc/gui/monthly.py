import datetime
from PySide2 import QtCore, QtWidgets
import rtlib
import rtlib.server
import apputils
import client
from client.qt import winlist


def rtapp_report_export(reportname):
    app = QtCore.QCoreApplication.instance()
    if hasattr(app, "report_export"):
        return app.report_export(reportname, app.session, app.exports_dir)


class Exporter(QtWidgets.QDialog):
    ID = "pyhacc_reporting_monthly_status"
    TITLE = "Monthly Status Reports"
    RPT1_BALANCE_SHEET = "api/gledger/balance-sheet"
    RPT2_DETAIL_PL = "api/gledger/detailed-pl"
    RPT3_INTERVAL_PL = "api/gledger/interval-p-and-l"
    RPT4_GIVING_SUMMARY = "api/transactions/account-summary"

    def __init__(self, state, parent=None):
        super(Exporter, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowIcon(QtWidgets.QApplication.instance().icon)
        self.setWindowTitle(self.TITLE)
        winlist.register(self, self.ID)

        self.backgrounder = apputils.Backgrounder(self)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.form = QtWidgets.QFormLayout()

        self.date_edit = apputils.construct("date")

        today = datetime.date.today()
        self.default_date = today - datetime.timedelta(days=today.day)
        self.date_edit.setValue(self.default_date)

        self.form.addRow("Month End:", self.date_edit)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.btn_close = self.buttons.addButton(QDB.Close)
        self.btn_close.clicked.connect(self.close)
        self.btn_export_all = self.buttons.addButton("Export All", QDB.ActionRole)
        self.btn_export_all.clicked.connect(self.cmd_export_all)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttons)

        self.client = state.session.std_client()

        self.geo = apputils.WindowGeometry(self, size=True, position=False)

        self.refresh_data()

    def refresh_data(self):
        defdate = self.date_edit.value()
        monthbegin = datetime.date(defdate.year, defdate.month, 1)
        yearbegin = datetime.date(defdate.year, 1, 1)

        offering = self.client.get("api/accounts/by-reference", reference="E_OFFER")

        self.btn_export_all.setEnabled(False)
        self.end_count = 0
        self.results = {}

        self.backgrounder(
            self.load_rpt1, self.client.get, self.RPT1_BALANCE_SHEET, date=defdate
        )
        self.backgrounder(
            self.load_rpt2,
            self.client.get,
            self.RPT2_DETAIL_PL,
            date1=monthbegin,
            date2=defdate,
        )
        self.backgrounder(
            self.load_rpt3,
            self.client.get,
            self.RPT3_INTERVAL_PL,
            ending_date=defdate,
            intervals=3,
            length=6,
        )
        self.backgrounder(
            self.load_rpt4,
            self.client.get,
            self.RPT4_GIVING_SUMMARY,
            date1=yearbegin,
            date2=defdate,
            account=offering.main_table().rows[0].id,
        )

    def end_report(self, which):
        try:
            content = yield
            self.results[which] = content
            self.end_count += 1

            if self.end_count >= 4:
                self.btn_export_all.setEnabled(True)
        except:
            apputils.exception_message(
                self, f"There was an error loading {self.TITLE}."
            )

    def load_rpt1(self):
        yield from self.end_report("balance-sheet")

    def load_rpt2(self):
        yield from self.end_report("expense-income-details")

    def load_rpt3(self):
        yield from self.end_report("rexpense-income-6months")

    def load_rpt4(self):
        yield from self.end_report("ytd-charitable-giving")

    def cmd_export_all(self):
        # get subdir
        exportdir = client.LocalDirectory(tail="MonthlyStatus")

        defdate = self.date_edit.value()
        # iterate reports and export
        for key in self.results.keys():
            content = self.results[key]
            # fname = exportdir.user_output_filename(key, 'xlsx')
            fname = exportdir.join(f"{key}-{defdate:%b%d}.xlsx")
            view = rtlib.server.uview_from_client_table(content.main_table())
            rform = content.keys.get("report-formats", [])
            if len(rform) > 0:
                export = rtapp_report_export(rform[0])
                export.export(fname, view, content, hyperlinks=False)
            else:
                rtlib.server.export_view(
                    fname, view, content.keys["headers"], hyperlinks=False
                )

        # show subdir
        exportdir.show_browser()

    def closeEvent(self, event):
        winlist.unregister(self)
        return super(Exporter, self).closeEvent(event)
