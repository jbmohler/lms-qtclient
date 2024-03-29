import time
from PySide6 import QtCore, QtWidgets, QtGui
import apputils
import client.qt as qt


def show_connection_error(parent, message, r):
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())
    msgBox.setIcon(QtWidgets.QMessageBox.Critical)

    msgBox.setText(f"{message}\n\nWeb status code:  {r.status_code}\nURL:  {r.url}")
    msgBox.setDetailedText(r.text)

    msgBox.exec_()


class ServerDiagnostics(QtWidgets.QDialog):
    def __init__(self, parent, session):
        super(ServerDiagnostics, self).__init__(parent)

        self.setWindowTitle("Server Diagnostics")
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

        self.form.addRow("Server:", self.server_edit)
        self.form.addRow("Server Version:", self.version_edit)
        self.form.addRow("SQL Version:", self.sql_version_edit)
        self.form.addRow("Average Ping Time:", self.avg_ping_time_edit)
        self.form.addRow("Maximum Ping Time:", self.max_ping_time_edit)

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
        self.layout.addWidget(
            QtWidgets.QLabel(
                "Pings every second with statistics updated over two minute window."
            )
        )
        self.layout.addWidget(self.buttons)

    def closeEvent(self, event):
        self.timer.stop()
        super(ServerDiagnostics, self).closeEvent(event)

    def load_version(self):
        try:
            payload = self.client.get("api/info")
            self.version_edit.setText(payload.keys["version"])
            self.sql_version_edit.setText(payload.keys["sql_version"])
        except:
            qt.exception_message(self, "Error getting server info")

    def ping_server(self):
        x1 = time.time()
        r = self.session.get(self.session.prefix("api/ping"))
        if r.status_code != 200:
            self.max_ping_time_edit.setText(f"ERROR:  {r.status_code}")
        x2 = time.time()
        if r.status_code == 200:
            self.ping_times.append(x2 - x1)
            self.ping_times = self.ping_times[-120:]

            avg = sum(self.ping_times) / len(self.ping_times)
            mx = max(self.ping_times)
            ms = lambda t: f"{t * 1000.0:.1f} ms"

            self.avg_ping_time_edit.setText(ms(avg))
            self.max_ping_time_edit.setText(ms(mx))


def server_diagnostics(parent, session):
    s = ServerDiagnostics(parent, session)
    s.exec_()
    s.close()


class RtxLoginDialog(QtWidgets.QDialog):
    ID = "rtx-login-dialog"
    TITLE = "Yenot Sign-on"

    def __init__(self, parent, session, settings_group=None, allow_offline=False):
        super(RtxLoginDialog, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)

        self.session = session

        self.settings_group = settings_group
        self.allow_offline = allow_offline
        app = QtCore.QCoreApplication.instance()
        self.setWindowTitle(app.applicationName())

        self.mode = "login"

        self.rtx_server_edit = QtWidgets.QLineEdit()
        self.rtx_server_edit.setMinimumWidth(apputils.get_char_width() * 40)
        self.rtx_user_edit = QtWidgets.QLineEdit()
        self.rtx_password_edit = QtWidgets.QLineEdit()
        self.rtx_password_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.rtx_pin2fa_edit = QtWidgets.QLineEdit()
        self.rtx_save_device_token = QtWidgets.QCheckBox(
            "&Remember this login on this device"
        )

        self.main = QtWidgets.QVBoxLayout(self)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons.addButton(QDB.Ok).clicked.connect(self.accept)
        self.buttons.addButton(QDB.Cancel).clicked.connect(self.reject)
        if self.allow_offline:
            self.buttons.addButton("&Offline", QDB.ApplyRole).clicked.connect(
                self.accept_offline
            )

        self.stack = QtWidgets.QStackedWidget()

        self.login = QtWidgets.QWidget()

        self.main_form = QtWidgets.QFormLayout(self.login)

        self.main_form.addRow("&Server:", self.rtx_server_edit)
        self.main_form.addRow("User &Name:", self.rtx_user_edit)
        self.main_form.addRow("&Password:", self.rtx_password_edit)
        self.main_form.addRow(self.rtx_save_device_token)

        self.stack.addWidget(self.login)

        self.confirm = QtWidgets.QWidget()

        self.confirm_form = QtWidgets.QFormLayout(self.confirm)
        self.confirm_form.addRow("&2FA Confirmation:", self.rtx_pin2fa_edit)

        self.stack.addWidget(self.confirm)

        self.main.addWidget(self.stack)
        self.main.addWidget(self.buttons)

        settings = QtCore.QSettings()
        settings.beginGroup(self.settings_group)
        self.rtx_server_url = settings.value("rtx_server_url")
        self.rtx_user = settings.value("rtx_user")
        self.offline = False

        if self.rtx_server_url != None:
            self.rtx_server_edit.setText(self.rtx_server_url)
        if self.rtx_user != None:
            self.rtx_user_edit.setText(self.rtx_user)
            self.rtx_password_edit.setFocus(QtCore.Qt.OtherFocusReason)

        QtCore.QTimer.singleShot(0, self.center_myself)

    def center_myself(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geo = screen.geometry()
        self.move((geo.width() - self.width()) / 2, (geo.height() - self.height()) / 2)

    def accept_offline(self):
        self.offline = True
        self.rtx_user = None
        return super(RtxLoginDialog, self).accept()

    def accept(self):
        username = self.rtx_user_edit.text()
        password = self.rtx_password_edit.text()
        try:
            self.session.set_base_url(self.rtx_server_edit.text())
            self.session.authenticate(username, password)
        except:
            qt.exception_message(self, "Error logging in.")
            self.rtx_password_edit.selectAll()
            return

        if self.session.pending_2fa:
            self.mode = "2fa"
            self.stack.setCurrentIndex(1)

        if not self.session.pending_2fa:
            devtoken = self.rtx_save_device_token.isChecked()
            if devtoken:
                self.session.save_device_token()

            self.rtx_user = username.upper()

        if not self.session.pending_2fa:
            settings = QtCore.QSettings()
            settings.beginGroup(self.settings_group)
            settings.setValue("rtx_server_url", self.session.server_url)
            settings.setValue("rtx_user", username)

            return super(RtxLoginDialog, self).accept()


class TwoFactorPrompt(QtWidgets.QDialog):
    ID = "rtx-2fa-dialog"
    TITLE = "Yenot 2-FA Confirm"

    def __init__(self, parent, session, settings_group=None, allow_offline=False):
        super(TwoFactorPrompt, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)

        self.session = session

        self.settings_group = settings_group
        self.allow_offline = allow_offline
        app = QtCore.QCoreApplication.instance()
        self.setWindowTitle(app.applicationName())

        self.rtx_pin_edit = QtWidgets.QLineEdit()

        self.main = QtWidgets.QVBoxLayout(self)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons.addButton(QDB.Ok).clicked.connect(self.accept)
        self.buttons.addButton(QDB.Cancel).clicked.connect(self.reject)
        if self.allow_offline:
            self.buttons.addButton("&Offline", QDB.ApplyRole).clicked.connect(
                self.accept_offline
            )

        self.main_form = QtWidgets.QFormLayout()

        self.main_form.addRow("&Confirmation P:", self.rtx_server_edit)
        self.main_form.addRow("User &Name:", self.rtx_user_edit)
        self.main_form.addRow("&Password:", self.rtx_password_edit)
        self.main_form.addRow(self.rtx_save_device_token)

        self.main.addLayout(self.main_form)
        self.main.addWidget(self.buttons)
