import sys
import uuid
import traceback
from PySide2 import QtCore, QtWidgets
import cliutils
import apputils
import client


class ChangeListener:
    def __init__(self, backgrounder, client, loadfunc, channel):
        self.client = client
        self.backgrounder = backgrounder
        self.loadfunc = loadfunc
        self.channel = channel
        self.running = True

        self.chain_index = 0
        self.chain_key = uuid.uuid1().hex

        kwargs = {
            "key": self.chain_key,
            "channel": self.channel,
        }
        results = self.client.put("api/sql/changequeue", **kwargs)
        self.chain_index = results.keys["index"]

        self.chained_listen()

    def chained_listen(self):
        kwargs = {
            "key": self.chain_key,
            "channel": self.channel,
            "index": self.chain_index,
        }
        # TODO: cancel should work on self.client.get, but it does not.
        self.backgrounder.named[self.chain_key](
            self.chained_reload, self.client, "api/sql/changequeue", **kwargs
        )

    def chained_reload(self):
        try:
            changes = yield

            chlist = changes.main_table()
            if len(chlist.rows) > 0:
                for row in chlist.rows:
                    self.chain_index = row.index

                self.loadfunc()
        except client.RtxError:
            delay = 1000.0 * 1.5
        except Exception:
            delay = 1000.0 * 1.5
        else:
            delay = 0.0

        if self.running:
            QtCore.QTimer.singleShot(int(delay), self.chained_listen)

    def close(self):
        self.running = False
        self.backgrounder.named[self.chain_key].cancel()


class RtxTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent):
        app = QtWidgets.QApplication.instance()
        super(RtxTrayIcon, self).__init__(app.icon, parent)

        self.messageClicked.connect(self.show_error_log)

    def error_event(self, descr, data):
        self.showMessage(f"Error: {descr}", "See error log for details")
        if data != None:
            app = QtWidgets.QApplication.instance()
            app.session.report_python_traceback_event("Shell Client Error", descr, data)

    def show_error_log(self):
        app = QtWidgets.QApplication.instance()
        app.excepter.show()


def xlsx_start_file(parent, fname):
    cliutils.xdg_open(fname)


def exception_abandon():
    type_, value, tb = sys.exc_info()
    # Explicitly abandon these exceptions.  They happen for either explicit
    # user abort or program close.
    return isinstance(
        value,
        (client.RtxRequestCancellation, apputils.BackgrounderAbort, GeneratorExit),
    )


def exception_message(parent, message):
    if exception_abandon():
        return

    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())

    type_, value, tb = sys.exc_info()
    if isinstance(value, client.RtxServerError):
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText(f"{str(value)}")
    elif isinstance(value, client.RtxError):
        # Warning seems justified here since this is an exception.  However,
        # that's not entirely clear and maybe RtxError should offer a level
        # hint.
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText(f"{str(value)}")
    else:
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText(f"{message}\n\nException message:  {str(value)}")
        msgBox.setDetailedText("\n".join(traceback.format_exception(type_, value, tb)))

    msgBox.exec_()


def red_warning(parent, text):
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())
    msgBox.setIcon(QtWidgets.QMessageBox.Critical)

    splits = text.split("\n", 1)
    if len(splits) > 1:
        line1, rest = splits
        rest = rest.replace("\n", "<br />")
        formatted = f'<font size="24" color="red">{line1}</font><br />{rest}'
    else:
        formatted = f'<font size="24" color="red">{text}</font>'

    msgBox.setText(formatted)

    msgBox.exec_()


def to_be_implemented(parent, text):
    name = QtWidgets.QApplication.applicationName()
    QtWidgets.QMessageBox.information(parent, name, "IMPLEMENTATION STUB\n\n" + text)


def copy_friendly_information(parent, text):
    dlg = QtWidgets.QDialog(parent)
    name = QtWidgets.QApplication.applicationName()
    dlg.setWindowTitle(name)
    dlg.setMinimumSize(600, 230)
    dlg.main = QtWidgets.QVBoxLayout(dlg)
    dlg.edit = QtWidgets.QTextEdit()
    QDB = QtWidgets.QDialogButtonBox
    dlg.buttons = QDB(QDB.Ok)
    dlg.main.addWidget(dlg.edit)
    dlg.main.addWidget(dlg.buttons)
    dlg.buttons.accepted.connect(dlg.accept)
    dlg.edit.setText(text)
    dlg.exec_()
