import sys
import traceback
from PySide2 import QtWidgets
import cliutils
import apputils
import client

class RtxTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent):
        app = QtWidgets.QApplication.instance()
        super(RtxTrayIcon, self).__init__(app.icon, parent)

        self.messageClicked.connect(self.show_error_log)

    def error_event(self, descr, data):
        self.showMessage(f'Error: {descr}', 'See error log for details')
        if data != None:
            app = QtWidgets.QApplication.instance()
            app.session.report_python_traceback_event('Shell Client Error', descr, data)

    def show_error_log(self):
        app = QtWidgets.QApplication.instance()
        app.excepter.show()

def xlsx_start_file(parent, fname):
    cliutils.xdg_open(fname)
    apputils.message(parent, 'Data export completed successfully.  See document in Excel.')


def exception_message(parent, message):
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())

    type_, value, tb = sys.exc_info()
    if isinstance(value, client.RtxServerError):
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText(f'{str(value)}')
    elif isinstance(value, client.RtxError):
        # Warning seems justified here since this is an exception.  However,
        # that's not entirely clear and maybe RtxError should offer a level
        # hint.
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText(f'{str(value)}')
    else:
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText(f'{message}\n\nException message:  {str(value)}')
        msgBox.setDetailedText('\n'.join(traceback.format_exception(type_, value, tb)))

    msgBox.exec_()

def red_warning(parent, text):
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())
    msgBox.setIcon(QtWidgets.QMessageBox.Critical)

    splits = text.split('\n', 1)
    if len(splits) > 1:
        line1, rest = splits
        rest = rest.replace('\n', '<br />')
        formatted = f'<font size="24" color="red">{line1}</font><br />{rest}'
    else:
        formatted = f'<font size="24" color="red">{text}</font>'

    msgBox.setText(formatted)

    msgBox.exec_()

def to_be_implemented(parent, text):
    name = QtWidgets.QApplication.applicationName()
    QtWidgets.QMessageBox.information(parent, name, 'IMPLEMENTATION STUB\n\n'+text)

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
