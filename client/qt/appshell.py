import sys
import os.path
import platform
import functools
import collections
from PySide6 import QtCore, QtGui, QtWidgets
import rtlib
import apputils
import qtviews
import client
import apputils.rtxassets
from . import serverdlgs
from . import utils
from . import about
from . import plugpoint
from . import reportdock
from . import reports
from . import winlist


class ClientURLMenuItem:
    def __init__(self, item_name, client_url, auth_name, shortcut=None):
        self.item_name = item_name
        self.client_url = client_url
        self.auth_name = auth_name
        self.shortcut = shortcut

    def action(self, parent):
        act = QtGui.QAction(self.item_name, parent)
        act.triggered.connect(lambda: parent.handle_url(self.client_url))
        if self.shortcut:
            act.setShortcut(self.shortcut)
        return act


class SeparatorMenuItem:
    def __init__(self):
        self.auth_name = None

    def action(self, parent):
        act = QtGui.QAction(parent)
        act.setSeparator(True)
        return act


class DocumentThread(QtCore.QObject):
    open_document = QtCore.Signal(object)

    def __init__(self, mainwin):
        super(DocumentThread, self).__init__()
        self._mainwin = mainwin

    def open(self, obj):
        self._mainwin.activateWindow()
        self._mainwin.raise_()
        self.open_document.emit(obj)


class ShellWindow(QtWidgets.QMainWindow, qtviews.TabbedWorkspaceMixin):
    ID = "main-window"

    def __init__(self, parent=None):
        super(ShellWindow, self).__init__(parent)
        self.initTabbedWorkspace()

        self.setWindowIcon(QtWidgets.QApplication.instance().icon)
        self.setWindowTitle(QtWidgets.QApplication.instance().applicationName())
        self.setObjectName(self.ID)
        winlist.register(self, self.ID)

        self.report_manager = None
        self.pending_urls = []
        self.menu_actions = []
        self.submenus = {}
        self.statics = []

        statstypes = [
            ("count", "&Count"),
            ("total", "&Total"),
            ("average", "&Average"),
            ("minimum", "Mi&nimum"),
            ("maximum", "Ma&ximum"),
        ]
        self.statistics = QtWidgets.QLabel("")
        self.statistics.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.statistics.actions_stattypes = collections.OrderedDict()
        for stat, label in statstypes:
            act = QtGui.QAction(label, self)
            act.setCheckable(True)
            act.setChecked(stat == "total")
            self.statistics.actions_stattypes[stat] = act
            self.statistics.addAction(act)

        status = self.statusBar()
        status.statistics = self.statistics
        status.addPermanentWidget(self.statistics)
        # status.addPermanentWidget(QtWidgets.QLabel('Server {}'.format(client.__version__)))
        self.server_connection = QtWidgets.QLabel("Not Connected")
        self.server_connection.linkActivated.connect(
            lambda url: plugpoint.show_link_parented(self, url)
        )
        status.addPermanentWidget(self.server_connection)

        screen = QtGui.QScreen()
        screensize = screen.availableGeometry()
        self.resize(QtCore.QSize(screensize.width() * 0.7, screensize.height() * 0.7))

        self.geo = apputils.WindowGeometry(self)

    def add_schematic_menu(self, mbar, menu_name, schematic):
        applicable = []
        for item in schematic:
            if item.auth_name == None or self.session.authorized(item.auth_name):
                applicable.append(item)

        sep_indices = [
            index
            for index, item in enumerate(applicable)
            if isinstance(item, SeparatorMenuItem)
        ]

        if len(sep_indices) == len(applicable):
            # empty menu -- no authorized items
            return

        sep_indices.append(-1)

        excess = []
        for index, item in enumerate(applicable):
            if index - 1 in sep_indices and index in sep_indices:
                excess.append(index)
        for index in reversed(excess):
            del applicable[index]
        while isinstance(applicable[-1], SeparatorMenuItem):
            del applicable[-1]

        mkey = menu_name.replace("&", "")
        if mkey in self.submenus:
            menu = self.submenus[mkey]
            applicable.insert(0, SeparatorMenuItem())
        else:
            menu = mbar.addMenu(menu_name)
            self.submenus[mkey] = menu
        for item in applicable:
            act = item.action(self)
            self.menu_actions.append(act)
            menu.addAction(act)

    def construct_file_menu(self, menu):
        self.action_exit = QtGui.QAction("E&xit", self)
        self.action_exit.triggered.connect(self.close)

        self.action_exit_all = QtGui.QAction("Exit &All", self)
        self.action_exit_all.setShortcut("Ctrl+F12")
        self.action_exit_all.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.action_exit_all.triggered.connect(self.close_all)

        self.action_weblogin = QtGui.QAction("&Web Login", self)
        self.action_weblogin.triggered.connect(
            lambda: plugpoint.show_link_parented(self, self.session.prefix(""))
        )

        self.action_userprofile = QtGui.QAction("&User Profile", self)
        self.action_userprofile.triggered.connect(self.cmd_edit_userprofile)

        self.action_exports = QtGui.QAction("View &Export Directory", self)
        self.action_exports.triggered.connect(lambda: self.exports_dir.show_browser())

        self.menu_file = menu.addMenu("&File")
        self.menu_file.addAction("&Reports").triggered.connect(self.show_reports)
        self.menu_file.addAction(self.action_exports)
        self.menu_file.addAction(self.action_weblogin)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_userprofile)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        self.menu_file.addAction(self.action_exit_all)

    def construct_window_menu(self, menu):
        self.action_close_current = QtGui.QAction("&Close Current Tab", self)
        self.action_close_current.setShortcut(QtGui.QKeySequence("Ctrl+F4"))
        self.action_close_current.triggered.connect(self.close_current)

        self.window_actions = []

        self.menu_window = menu.addMenu("&Window")
        self.menu_window.addAction(self.action_close_current)
        self.menu_window_sep = self.menu_window.addSeparator()
        self.menu_window.aboutToShow.connect(self.update_window_menu)

    def construct_help_menu(self, menu):
        self.action_about = QtGui.QAction("&About", self)
        self.action_about.triggered.connect(lambda: about.about_box(self, "rtx shell"))

        self.action_syshelp = QtGui.QAction("&Source Code", self)
        self.action_syshelp.triggered.connect(
            lambda: plugpoint.show_link_parented(
                self, self.session.prefix("lms/technical")
            )
        )

        self.action_serverdiag = QtGui.QAction("Server && &Connection", self)
        self.action_serverdiag.triggered.connect(
            lambda: serverdlgs.server_diagnostics(self, self.session)
        )

        self.action_exceptions = QtGui.QAction("View &Exception Log", self)
        app = QtCore.QCoreApplication.instance()
        self.action_exceptions.triggered.connect(app.excepter.show)

        self.menu_help = menu.addMenu("&Help")
        self.menu_help.addAction(self.action_about)
        self.menu_help.addAction(self.action_syshelp)
        self.menu_help.addAction(self.action_serverdiag)
        self.menu_help.addAction(self.action_exceptions)

    def rtx_login(self):
        if not self.session.authenticated():
            dlg = serverdlgs.RtxLoginDialog(
                self, self.session, settings_group="Example"
            )
            if dlg.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
                pass
            else:
                self.close()
                return False
        self.post_login()

    def start_doc_server(self):
        if platform.system() == "Windows":
            return

        import client.cmdserver_unix as cmdserver

        cmdserver.launch_document_server(self.receiver)

    def close_doc_server(self):
        if platform.system() == "Windows":
            return

        import client.cmdserver_unix as cmdserver

        cmdserver.close_document_server()

    def receiver(self):
        self.doc_server = DocumentThread(self)
        self.doc_server.open_document.connect(self.handle_url)
        return self.doc_server

    def handle_url(self, url):
        plugpoint.show_link_parented(self, QtCore.QUrl(url))

    def ensure_refreshed(self):
        self.session.session_refresh()
        self.post_login()

    def post_login(self):
        self.setup_menu_bar()

        s = self.session
        conn_info = f"<a href=\"{s.prefix('')}\">{s.server_url}</a> {s.rtx_username}"
        self.server_connection.setText(conn_info)

        plugpoint.plugin_initialize(self)

        for url in self.pending_urls:
            self.handle_url(url)
        # clear this so that post_login is idempotent
        self.pending_urls = []

        # refresh the session & reports every 45 minutes
        # - new menu based on updated permissions
        # - update report list based on permissions
        ms = 52 * 60 * 1000
        self.refresh_timer = QtCore.QTimer.singleShot(ms, self.ensure_refreshed)

    def setup_menu_bar(self):
        # This function is intended to be idempotent so that new permissions
        # are reflected on token refresh.
        self.menuBar().clear()
        self.menu_actions = []
        self.submenus = {}

        self.construct_file_menu(self.menuBar())
        self.submenus["File"] = self.menu_file
        # self.submenus["Window"] = self.menu_window
        # self.submenus["Help"] = self.menu_help

        ctors = {
            "ClientURLMenuItem": ClientURLMenuItem,
            "SeparatorMenuItem": SeparatorMenuItem,
        }

        for menuname, items in plugpoint.get_plugin_menus():
            schematic = [ctors[n](*args) for n, args in items]
            self.add_schematic_menu(self.menuBar(), menuname, schematic)

        self.construct_window_menu(self.menuBar())
        self.construct_help_menu(self.menuBar())

        if self.report_manager is None:
            self.report_manager = reports.ReportsManager(
                self.session, self.exports_dir, self
            )

            self.report_dock = reportdock.ReportsDock(self.session, self.exports_dir)
            self.report_dock.main_window = self
            self.report_dock.hide()

            self.addWorkspaceWindow(
                self.report_dock,
                self.report_dock.TITLE,
                settingsKey=self.report_dock.ID,
                addto="dock",
            )
        else:
            self.report_dock.reload_reports()

        return True

    def cmd_edit_userprofile(self):
        self.handle_url("rtauth:user/login/edit")

    def show_reports(self):
        self.report_dock.show()

    def close_current(self):
        self.closeTab(self.workspace.currentIndex())

    def tab_by_id(self, tab_id):
        w = self.workspaceWindowByKey(tab_id)
        return None, w
        # TODO - research whether I need a static
        for widget in self.statics:
            if widget._shell_tab_id == tab_id:
                return None, widget
        return None, None

    def adopt_tab(self, widget, shell_id, tab_title, static=False, addto=None):
        self.addWorkspaceWindow(
            widget, title=tab_title, settingsKey=shell_id, addto=addto
        )
        return

        # TODO need a static?

        if static:
            self.statics.append(widget)

    def disown_tab(self, widget):
        # nothing to do, let it just go out of scope
        pass

    def update_window_menu(self):
        self.action_close_current.setEnabled(self.workspace.count() > 0)

        for act in self.window_actions:
            self.menu_window.removeAction(act)

        self.window_actions = self.tabsInWindowMenu(self.menu_window)

        """
        static_ids = [w._shell_tab_id for w in self.statics]

        # clear out old window actions
        winacts = [act for act in self.menu_window.actions() if hasattr(act, '_shell_tab_id')]
        for act in winacts:
            if act._shell_tab_id in static_ids:
                continue
            self.menu_window.removeAction(act)

        # make new ones
        nonstatics = []
        for index in range(self.central.count()):
            widget = self.central.widget(index)
            if widget._shell_tab_id not in static_ids and hasattr(widget, '_shell_fg_action'):
                nonstatics.append(widget)

        for index, widget in enumerate(nonstatics):
            action = widget._shell_fg_action
            if index < 10:
                action.setText('&{} {}'.format(index+1, widget.windowTitle()))
            else:
                action.setText('{}'.format(widget.windowTitle()))
            self.menu_window.addAction(action)
            """

    def closeEvent(self, event):
        for index in range(self.workspace.count()):
            widget = self.workspace.widget(index)
            widget.close()
        winlist.unregister(self)
        self.close_doc_server()
        return super(ShellWindow, self).closeEvent(event)

    def close_all(self):
        winlist.close_all()


def basic_shell_window(app, session=None, document=None):
    sys.excepthook = apputils.guiexcepthook
    app.session = session

    winlist.init(ShellWindow.ID)

    f = ShellWindow()
    f.exports_dir = app.exports_dir
    f.session = app.session

    if document:
        f.pending_urls.append(document)

    QtCore.QTimer.singleShot(0, lambda: f.rtx_login())
    QtCore.QTimer.singleShot(0, lambda: f.start_doc_server())
    f.show()

    tray = utils.RtxTrayIcon(app)
    tray.show()

    # ratchet up the error handling
    app.excepter = apputils.ExceptionLogger(app)
    app.excepter.error_event.connect(tray.error_event)
    sys.excepthook = app.excepter.excepthook

    app.exec_()

    app.session.close()

    tray.hide()
