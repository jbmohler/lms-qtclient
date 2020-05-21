import time
from PySide2 import QtCore, QtWidgets
from . import utils

def show_connection_error(parent, message, r):
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())
    msgBox.setIcon(QtWidgets.QMessageBox.Critical)

    msgBox.setText('{}\n\nWeb status code:  {}\nURL:  {}'.format(message, r.status_code, r.url))
    msgBox.setDetailedText(r.text)

    msgBox.exec_()

class ServerDiagnostics(QtWidgets.QDialog):
    def __init__(self, parent, session):
        super(ServerDiagnostics, self).__init__(parent)

        self.setWindowTitle('Server Diagnostics')
        self.setMinimumSize(350, 150)
        self.session = session
        self.client = session.std_client()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.form = QtWidgets.QFormLayout()

        self.server_edit = QtWidgets.QLineEdit()
        self.version_edit = QtWidgets.QLineEdit()
        self.sql_version_edit = QtWidgets.QLineEdit()
        self.sql_version_edit.setMinimumWidth(350)
        self.avg_ping_time_edit = QtWidgets.QLineEdit()
        self.max_ping_time_edit = QtWidgets.QLineEdit()

        self.server_edit.setText(self.client.session.server_url)

        self.form.addRow('Server:', self.server_edit)
        self.form.addRow('Server Version:', self.version_edit)
        self.form.addRow('SQL Version:', self.sql_version_edit)
        self.form.addRow('Average Ping Time:', self.avg_ping_time_edit)
        self.form.addRow('Maximum Ping Time:', self.max_ping_time_edit)

        self.ping_times = []

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.ping_server)
        self.timer.start()

        QtCore.QTimer.singleShot(0, self.load_version)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QDB.Ok)
        self.buttons.accepted.connect(self.accept)

        self.layout.addLayout(self.form)
        self.layout.addWidget(QtWidgets.QLabel('Pings every second with statistics updated over two minute window.'))
        self.layout.addWidget(self.buttons)

    def closeEvent(self, event):
        self.timer.stop()
        super(ServerDiagnostics, self).closeEvent(event)

    def load_version(self):
        try:
            payload = self.client.get('api/info')
            self.version_edit.setText(payload.keys['version'])
            self.sql_version_edit.setText(payload.keys['sql_version'])
        except:
            utils.exception_message(self, 'Error getting server info')

    def ping_server(self):
        x1 = time.time()
        r = self.session.get(self.session.prefix('api/ping'))
        if r.status_code != 200:
            self.max_ping_time_edit.setText('ERROR:  {}'.format(r.status_code))
        x2 = time.time()
        if r.status_code == 200:
            self.ping_times.append(x2-x1)
            self.ping_times = self.ping_times[-120:]

            avg = sum(self.ping_times)/len(self.ping_times)
            mx = max(self.ping_times)
            ms = lambda t: '{:.1f} ms'.format(t*1000.)

            self.avg_ping_time_edit.setText(ms(avg))
            self.max_ping_time_edit.setText(ms(mx))

def server_diagnostics(parent, session):
    s = ServerDiagnostics(parent, session)
    s.exec_()
    s.close()

class RtxLoginDialog(QtWidgets.QDialog):
    def __init__(self, parent, session, settings_group=None, allow_offline=False):
        super(RtxLoginDialog, self).__init__(parent)

        self.session = session

        self.settings_group = settings_group
        self.allow_offline = allow_offline
        app = QtCore.QCoreApplication.instance()
        self.setWindowTitle(app.applicationName())

        self.rtx_user_edit = QtWidgets.QLineEdit()
        self.rtx_password_edit = QtWidgets.QLineEdit()
        self.rtx_password_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        self.main = QtWidgets.QVBoxLayout(self)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons.addButton(QDB.Ok).clicked.connect(self.accept)
        self.buttons.addButton(QDB.Cancel).clicked.connect(self.reject)
        if self.allow_offline:
            self.buttons.addButton('&Offline', QDB.ApplyRole).clicked.connect(self.accept_offline)

        self.main_form = QtWidgets.QFormLayout()

        self.main_form.addRow('User &Name:', self.rtx_user_edit)
        self.main_form.addRow('&Password:', self.rtx_password_edit)

        self.main.addLayout(self.main_form)
        self.main.addWidget(self.buttons)

        settings = QtCore.QSettings()
        settings.beginGroup(self.settings_group)
        self.rtx_user = settings.value('rtx_user')
        self.offline = False

        if self.rtx_user != None:
            self.rtx_user_edit.setText(self.rtx_user)
            self.rtx_password_edit.setFocus(QtCore.Qt.OtherFocusReason)

    def accept_offline(self):
        self.offline = True
        self.rtx_user = None
        return super(RtxLoginDialog, self).accept()

    def accept(self):
        username = self.rtx_user_edit.text()
        password = self.rtx_password_edit.text()
        try:
            self.session.authenticate(username, password)
            self.rtx_user = username.upper()
        except:
            utils.exception_message(self, 'Error logging in.')
            self.rtx_password_edit.selectAll()
            return

        settings = QtCore.QSettings()
        settings.beginGroup(self.settings_group)
        settings.setValue('rtx_user', username)

        return super(RtxLoginDialog, self).accept()
