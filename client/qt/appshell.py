import os
import sys
import collections
from PySide2 import QtCore, QtGui, QtWidgets
import rtlib
import apputils
import client
import apputils.rtxassets
from . import serverdlgs
from . import utils
from . import about
from . import gridmgr
from . import reportdock
from . import reports
from . import winlist

class ClientURLMenuItem:
    def __init__(self, item_name, client_url, auth_name):
        self.item_name = item_name
        self.client_url = client_url
        self.auth_name = auth_name

    def action(self, parent):
        act = QtWidgets.QAction(self.item_name, parent)
        act.triggered.connect(lambda: parent.handle_url(self.client_url))
        return act

class SeparatorMenuItem:
    def __init__(self):
        self.auth_name = None

    def action(self, parent):
        act = QtWidgets.QAction(parent)
        act.setSeparator(True)
        return act
    

class ShellWindow(QtWidgets.QMainWindow):
    ID = 'main-window'

    def __init__(self, parent=None):
        super(ShellWindow, self).__init__(parent)

        self.setWindowIcon(QtWidgets.QApplication.instance().icon)
        self.setWindowTitle(QtWidgets.QApplication.instance().applicationName())
        self.setObjectName(self.ID)
        winlist.register(self, self.ID)

        self.menu_actions = []

        self.central = QtWidgets.QTabWidget()
        self.central.setTabsClosable(True)
        self.central.setDocumentMode(True)
        self.central.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.central)

        self.menu_actions = []

        self.statics = []

        statstypes = [ \
                ('count', '&Count'),
                ('total', '&Total'),
                ('average', '&Average'),
                ('minimum', 'Mi&nimum'),
                ('maximum', 'Ma&ximum')]
        self.statistics = QtWidgets.QLabel('')
        self.statistics.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.statistics.actions_stattypes = collections.OrderedDict()
        for stat, label in statstypes:
            act = QtWidgets.QAction(label, self)
            act.setCheckable(True)
            act.setChecked(stat == 'total')
            self.statistics.actions_stattypes[stat] = act
            self.statistics.addAction(act)

        status = self.statusBar()
        status.statistics = self.statistics
        status.addPermanentWidget(self.statistics)
        #status.addPermanentWidget(QtWidgets.QLabel('Server {}'.format(client.__version__)))
        self.server_connection = QtWidgets.QLabel('Not Connected')
        # TODO:  fix this -- if you comment this out, it crashes
        #self.server_connection.linkActivated.connect(os.startfile)
        status.addPermanentWidget(self.server_connection)

        self.report_dock = QtWidgets.QDockWidget(reportdock.ReportsDock.TITLE, self)
        self.report_dock.setObjectName(reportdock.ReportsDock.ID)
        self.report_dock.hide()
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.report_dock)

        desktop = QtWidgets.QDesktopWidget()
        screensize = desktop.availableGeometry(self)
        self.resize(QtCore.QSize(screensize.width()*0.7, screensize.height()*0.7))

        self.geo = apputils.WindowGeometry(self)

    def add_schematic_menu(self, mbar, menu_name, schematic):
        applicable = []
        for item in schematic:
            if item.auth_name == None or self.session.authorized(item.auth_name):
                applicable.append(item)

        sep_indices = [index for index, item in enumerate(applicable) if isinstance(item, SeparatorMenuItem)]

        if len(sep_indices) == len(applicable):
            # empty menu -- no authorized items
            return

        sep_indices.append(-1)

        excess = []
        for index, item in enumerate(applicable):
            if index-1 in sep_indices and index in sep_indices:
                excess.append(index)
        for index in reversed(excess):
            del applicable[index]
        while isinstance(applicable[-1], SeparatorMenuItem):
            del applicable[-1]

        menu = mbar.addMenu(menu_name)
        for item in applicable:
            act = item.action(self)
            self.menu_actions.append(act)
            menu.addAction(act)

    def construct_file_menu(self, menu):
        self.action_exit = QtWidgets.QAction('E&xit', self)
        self.action_exit.triggered.connect(self.close)

        self.action_exit_all = QtWidgets.QAction('Exit &All', self)
        self.action_exit_all.setShortcut('Ctrl+F12')
        self.action_exit_all.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.action_exit_all.triggered.connect(self.close_all)

        self.action_exports = QtWidgets.QAction('View &Export Directory', self)
        self.action_exports.triggered.connect(lambda: self.exports_dir.show_browser())

        self.menu_file = menu.addMenu('&File')
        self.menu_file.addAction('&Reports').triggered.connect(self.show_reports)
        self.menu_file.addAction(self.action_exports)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)
        self.menu_file.addAction(self.action_exit_all)

    def construct_window_menu(self, menu):
        self.action_close_current = QtWidgets.QAction('&Close Current Tab', self)
        self.action_close_current.setShortcut(QtGui.QKeySequence('Ctrl+F4'))
        self.action_close_current.triggered.connect(self.close_current)

        self.menu_window = menu.addMenu('&Window')
        self.menu_window.addAction(self.action_close_current)
        self.menu_window_sep = self.menu_window.addSeparator()
        self.menu_window.aboutToShow.connect(self.update_window_menu)

    def construct_help_menu(self, menu):
        self.action_about = QtWidgets.QAction('&About', self)
        self.action_about.triggered.connect(lambda: about.about_box(self, 'rtx shell'))

        self.action_syshelp = QtWidgets.QAction('&Technical Manual', self)
        self.action_syshelp.triggered.connect(lambda: winlist.show_link_parented(self, self.session.prefix('docs/index.html')))

        self.action_serverdiag = QtWidgets.QAction('Server && &Connection', self)
        self.action_serverdiag.triggered.connect(lambda: serverdlgs.server_diagnostics(self, self.session))

        self.action_exceptions = QtWidgets.QAction('View &Exception Log', self)
        app = QtCore.QCoreApplication.instance()
        self.action_exceptions.triggered.connect(app.excepter.show)

        self.menu_help = menu.addMenu('&Help')
        self.menu_help.addAction(self.action_about)
        self.menu_help.addAction(self.action_syshelp)
        self.menu_help.addAction(self.action_serverdiag)
        self.menu_help.addAction(self.action_exceptions)

    def rtx_login(self, presession=None):
        if presession != None:
            try:
                self.session.authenticate(presession.username, presession.password)
            except:
                utils.exception_message(self, 'Error logging in.')
                self.close()
                return False
        else:
            dlg = serverdlgs.RtxLoginDialog(self, self.session, settings_group='Example')
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                pass
            else:
                self.close()
                return False
        self.post_login()

    def handle_deferred_urls(self):
        for url in self.deferred_urls:
            self.handle_url(url)

    def handle_url(self, url):
        gridmgr.show_link_parented(self, QtCore.QUrl(url))

    def post_login(self):
        s = self.session
        self.server_connection.setText('<a href="{}">{}</a> {}'.format(s.prefix(''), s.server_url, s.rtx_user))

        self.construct_file_menu(self.menuBar())

        ctors = {
                'ClientURLMenuItem': ClientURLMenuItem,
                'SeparatorMenuItem': SeparatorMenuItem}

        for menuname, items in gridmgr.get_menus():
            schematic = [ctors[n](*args) for n, args in items]
            self.add_schematic_menu(self.menuBar(), menuname, schematic)

        self.construct_window_menu(self.menuBar())
        self.construct_help_menu(self.menuBar())

        self.report_dock.setWidget(reportdock.ReportsDock(self.session, self.exports_dir))
        self.report_dock.widget().main_window = self
        act = self.report_dock.toggleViewAction()
        act.setText('&Report List')
        self.menu_window.insertAction(self.menu_window_sep, act)

        self.report_manager = reports.ReportsManager(self.session, self.exports_dir, self)

        return True

    def show_reports(self):
        self.report_dock.show()

    def close_tab(self, index):
        tab = self.central.widget(index)
        if tab.close():
            self.disown_tab(tab)
            self.central.removeTab(index)

    def close_current(self):
        self.close_tab(self.central.currentIndex())

    def tab_by_id(self, tab_id):
        for index in range(self.central.count()):
            widget = self.central.widget(index)
            if widget._shell_tab_id == tab_id:
                return index, widget
        for widget in self.statics:
            if widget._shell_tab_id == tab_id:
                return None, widget
        return None, None

    def create_or_adopt_tab(self, widclass):
        if self.foreground_tab(widclass.ID):
            return

        w = widclass(self.session, self.exports_dir)
        self.adopt_tab(w, widclass.ID, widclass.TITLE)

    def foreground_tab(self, tab_id):
        index, widget = self.tab_by_id(tab_id)
        if widget != None:
            if index == None:
                index = self.central.addTab(widget, widget._shell_tab_title)
            self.central.setCurrentIndex(index)
        return index != None

    def adopt_tab(self, widget, shell_id, tab_title, static=False):
        widget._shell_tab_id = shell_id
        widget._shell_tab_title = tab_title
        widget._shell_fg_action = QtWidgets.QAction(self)
        widget._shell_fg_action._shell_tab_id = shell_id
        widget._shell_fg_action.triggered.connect(lambda w=widget._shell_tab_id: self.foreground_tab(w))

        if static:
            self.statics.append(widget)

        newindex = self.central.addTab(widget, tab_title)
        self.central.setCurrentIndex(newindex)

    def disown_tab(self, widget):
        # nothing to do, let it just go out of scope
        pass

    def update_window_menu(self):
        self.action_close_current.setEnabled(self.central.count() > 0)

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

    def closeEvent(self, event):
        for index in range(self.central.count()):
            widget = self.central.widget(index)
            widget.close()
        winlist.unregister(self)
        return super(ShellWindow, self).closeEvent(event)

    def close_all(self):
        winlist.close_all()

def qt_app_init():
    app = QtWidgets.QApplication([])
    app.setOrganizationDomain('rtxlib.com')
    app.setOrganizationName('RTX Library Authors')
    app.setApplicationName('RTX Application Shell')
    app.icon = QtGui.QIcon(':/apputils/rtxapp.ico')
    app.exports_dir = client.LocalDirectory(appname='RtxShell', tail='Exports')

    import pyhacc.gui as pg
    import client.qt.rtauth as rtauth

    rtlib.add_type_definition_plugin(pg.AccountingWidgetsPlugin())
    rtlib.add_type_definition_plugin(rtlib.BasicTypePlugin())
    rtlib.add_type_definition_plugin(apputils.BasicWidgetsPlugin())

    gridmgr.add_extension_plug(pg.AccountingExtensions())
    gridmgr.add_extension_plug(rtauth.RtAuthPlugs())

    app.report_sidebar = gridmgr.search_sidebar
    app.report_export = gridmgr.search_export

    return app

def rtx_main_window_embedded(session):
    winlist.init(ShellWindow.ID)

    app = QtCore.QCoreApplication.instance()
    app.session = session

    f = ShellWindow()
    f.exports_dir = app.exports_dir
    f.session = app.session
    QtCore.QTimer.singleShot(0, f.post_login)
    f.show()

    tray = utils.RtxTrayIcon(app)
    tray.show()

    excepthook_old = sys.excepthook

    # ratchet up the error handling
    app.excepter = apputils.ExceptionLogger(app)
    app.excepter.error_event.connect(tray.error_event)
    sys.excepthook = app.excepter.excepthook

    app.exec_()

    tray.hide()
    sys.excepthook = excepthook_old

def basic_shell_window(presession=None, document=None):
    sys.excepthook = apputils.guiexcepthook
    app = qt_app_init()
    app.session = client.RtxSession(presession.server)

    winlist.init(ShellWindow.ID)

    f = ShellWindow()
    f.exports_dir = app.exports_dir
    f.session = app.session
    QtCore.QTimer.singleShot(0, lambda: f.rtx_login(presession))
    f.show()

    tray = utils.RtxTrayIcon(app)
    tray.show()

    # ratchet up the error handling
    app.excepter = apputils.ExceptionLogger(app)
    app.excepter.error_event.connect(tray.error_event)
    sys.excepthook = app.excepter.excepthook

    if document != None:
        QtCore.QTimer.singleShot(0, lambda url=document: f.handle_url(url))

    app.exec_()

    app.session.close()

    tray.hide()
