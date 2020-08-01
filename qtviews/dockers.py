# -*- coding: utf-8 -*-
##############################################################################
#       Copyright (C) 2010, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################

import uuid
from PySide2 import QtCore, QtWidgets

class WindowMeta(object):
    def __init__(self, title, factory, settingsKey=None, fixedpos=False):
        self.title = title
        self.factory = factory
        self.fixedpos = fixedpos
        if settingsKey is None:
            self.settingsKey = factory
        else:
            self.settingsKey = settingsKey

    def is_detached(self):
        return self.settingsKey.startswith('detached_')

    def detach(self):
        self.settingsKey = 'detached_{0}'.format(uuid.uuid1().hex)

class Docker(QtWidgets.QDockWidget):
    def __init__(self, mainWindow, child):
        QtWidgets.QDockWidget.__init__(self)
        self.child = child
        self.mainWindow = mainWindow
        child._docker = self
        self.setWindowTitle(child._docker_meta.title)
        self.setObjectName(child._docker_meta.settingsKey)
        self.setWidget(child)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pnt: 
                self.mainWindow.workspaceContextMenuDocked(self.child, pnt))

class TabbedWorkspaceMixin(object):
    """
    This class is designed to be a mix-in for QtWidgets.QMainWindow.  It places a
    QTabWidget as the central widget.

    The viewFactory is a public dictionary mapping type names to callables for
    constructing the collection of widget.  This is used to prepare this
    instance to reconstruct a window layout saved from a QSettings profile
    section.
    """
    def initTabbedWorkspace(self):
        self.workspace = QtWidgets.QTabWidget()
        self.setCentralWidget(self.workspace)
        self.workspace.setDocumentMode(True)
        self.workspace.setTabsClosable(True)
        self.workspace.tabCloseRequested.connect(self.closeTab)

        self.workspace.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.workspace.customContextMenuRequested.connect(self.workspaceContextMenuTabbed)

        self.viewFactory = {}

        self.docked = []

    def updateViewFactory(self, mapping):
        """
        :param mapping:  dictionary of names to callables for instantiating
        views identified by that name.
        """
        self.viewFactory.update(mapping)

    def viewFactory(self, klass, settingsKey=None):
        """
        :param klass: view factory function for specific views
        :param settingsKey: an option key string for where to find the settings
            for this view
        """
        c = klass(settingsKey)
        self.addWorkspaceWindow(c.widget(), c.title(), c.settingsKey)

    def loadView(self, name, defaultTabs=None, defaultDocks=None, **kwargs):
        """
        Reload a view from a named settings profile (using QSettings).  If
        there are no saved settings in this setting profile, then load a
        default view as specified in the keyword arguments.

        Allowable keyword arguments for setting up the defaults include:

        :param defaultTabs:  a list of widget names in the viewFactory
            dictionary
        :param defaultDocks:  a list of widget names in the viewFactory to be
            constructed as docked windows in the QMainFrame
        """
        s = QtCore.QSettings()
        s.beginGroup(name)
        if "tabbed" in s.childKeys():
            defaultTabs = s.value("tabbed")
            if defaultTabs in [None, '']:
                defaultTabs = None
            else:
                defaultTabs = defaultTabs.split(';')
        if "docked" in s.childKeys():
            defaultDocks = s.value("docked")
            if defaultDocks in [None, ""]:
                defaultDocks = None
            else:
                defaultDocks = defaultDocks.split(';')

        if defaultTabs is not None:
            for x in defaultTabs:
                s.beginGroup(x)
                factory = s.value("factory", x)
                title = s.value("title", None)
                self.addWorkspaceWindow(factory, title=title, settingsKey=x)
                s.endGroup()
        if defaultDocks is not None:
            for x in defaultDocks:
                s.beginGroup(x)
                factory = s.value("factory", x)
                title = s.value("title", None)
                self.addWorkspaceWindow(factory, title=title, settingsKey=x, addto="dock")
                s.endGroup()

        if "geometry" in s.childKeys():
            self.restoreGeometry(s.value("geometry"))
        if "windowState" in s.childKeys():
            self.restoreState(s.value("windowState"))
        s.endGroup()

    def saveView(self, name):
        """
        This method saves the dock and tabs settings for restoration in the
        future.
        """
        s = QtCore.QSettings()
        s.beginGroup(name)
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())

        tabs = [w._docker_meta.settingsKey for w in self.windows("tabs") 
                if w._docker_meta.factory is not None]
        docks = [w._docker_meta.settingsKey for w in self.windows("docks") 
                if w._docker_meta.factory is not None]

        s.setValue("tabbed", ';'.join([t for t in tabs if t is not None]))
        s.setValue("docked", ';'.join([t for t in docks if t is not None]))

        for w in self.windows():
            if w._docker_meta.factory is not None:
                s.beginGroup(w._docker_meta.settingsKey)
                s.setValue('title', w._docker_meta.title)
                s.setValue('factory', w._docker_meta.factory)
                s.endGroup()

        s.endGroup()

    def addWorkspaceWindowOrSelect(self, widget, title=None, factory=None, settingsKey=None, addto=None):
        w = self.selectTab(widget)
        if w is None:
            self.addWorkspaceWindow(widget, title, factory, settingsKey, addto)

    def addWorkspaceWindow(self, widget, title=None, factory=None, settingsKey=None, addto=None, fixedpos=False):
        """
        Add a dock managed window.  Tabify or dock as according to settings.

        :param widget:  widget is a QtWidgets.QWidget derived class or a key in the
            viewFactory dictionary.  If widget is a key in the viewFactory
            dictionary, then the associated callable is used to construct the
            widget.
        :param addto: can be "dock" or "tab" to indicate adding the widget as a
            docked window or tabbed window respectively

        """
        if not isinstance(widget, QtWidgets.QWidget):
            assert factory == widget or factory == None, 'This is a bizarre API with a silly limitation'
            factory = widget
            widget = self.viewFactory[widget]()

        if title is None and hasattr(widget, 'title'):
            title = widget.title
        if factory is None and hasattr(widget, 'factory'):
            factory = widget.factory
        if settingsKey is None and hasattr(widget, 'settingsKey'):
            settingsKey = widget.settingsKey
        widget._docker_meta = WindowMeta(title, factory, settingsKey, fixedpos=fixedpos)
        if addto == "dock":
            self._addDocked(widget)
        else:
            self._addToTab(widget)

    def _addToTab(self, w):
        self.workspace.addTab(w, w._docker_meta.title)
        self.workspace.setCurrentWidget(w)
        w.show()
        w.setFocus()

    def _addDocked(self, w):
        self.docked.append(w)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, Docker(self, w))

    def windows(self, include=None):
        """
        Enumerate all windows managed by this TabbedWorkspaceMixin.

        :param include: defaults to including both tabbed and docked windows.
        Set to "docks" or "tabs" to limit the enumerated windows accordingly.
        """
        if include in [None, "tabs"]:
            for i in range(self.workspace.count()):
                yield self.workspace.widget(i)
        if include in [None, "docks"]:
            for d in self.docked:
                yield d

    def workspaceWindowByKey(self, settingsKey, include=None):
        """
        Search and return the first window matching the settingsKey.

        :param settingsKey: the settingsKey to match
        :param include: see :func:`windows`
        """
        ws = [w for w in self.windows(include) if
                w._docker_meta.settingsKey==settingsKey]
        if len(ws):
            return ws[0]
        return None

    def dockWorkspaceWindow(self, settingsKey):
        """
        Remove a tabbed window from the tab widget and add it as a dock window.
        """
        w = self.workspaceWindowByKey(settingsKey)
        print(settingsKey)
        if w is not None:
            self._addDocked(w)

    def undockWorkspaceWindow(self, settingsKey):
        """
        Remove a docked window from any docking area and add it to the central
        tab bar.
        """
        w = self.workspaceWindowByKey(settingsKey)
        if w is not None:
            self.removeDockWidget(w._docker)
            w._docker = None
            self.docked.remove(w)
            self._addToTab(w)

    def addSharedContextActions(self, w, menu):
        # rename, close, detach from command
        a = menu.addAction("Close")
        a.triggered.connect(lambda *args, key=w._docker_meta.settingsKey:
                self.closeWindow(w._docker_meta.settingsKey))

        a = menu.addAction("Rename")
        a.triggered.connect(lambda *args, key=w._docker_meta.settingsKey:
                self.renameWindow(key))

        if not w._docker_meta.is_detached():
            a = menu.addAction("Detach Visual Settings")
            a.triggered.connect(lambda *args, key=w._docker_meta.settingsKey:
                    self.detachVisualSettings(key))

    def workspaceContextMenuDocked(self, w, pnt):
        if w._docker_meta.fixedpos:
            return

        self.menu = QtWidgets.QMenu()

        a = self.menu.addAction("Tabify")
        a.triggered.connect(lambda *args, key=w._docker_meta.settingsKey:
                self.undockWorkspaceWindow(key))

        self.addSharedContextActions(w, self.menu)

        self.menu.popup(w._docker.mapToGlobal(pnt))

    def workspaceContextMenuTabbed(self, pnt):
        tb = self.workspace.tabBar()
        if self.workspace.currentIndex() >= 0 and tb.tabAt(pnt) == self.workspace.currentIndex():
            w = self.workspace.currentWidget()
            if w._docker_meta.fixedpos:
                return

            self.menu = QtWidgets.QMenu()

            a = self.menu.addAction("Add docked")
            a.triggered.connect(lambda *args, key=w._docker_meta.settingsKey:
                    self.dockWorkspaceWindow(key))

            self.addSharedContextActions(w, self.menu)
            
            self.menu.popup(self.workspace.mapToGlobal(pnt))

    def detachVisualSettings(self, key):
        w = self.workspaceWindowByKey(key)
        w._docker_meta.detach()

    def closeWindow(self, key):
        for i in range(self.workspace.count()):
            w = self.workspace.widget(i)
            if w._docker_meta.settingsKey == key:
                self.closeTab(i)
                break

        for w in self.docked:
            if w._docker_meta.settingsKey == key:
                self.removeDockWidget(w._docker)
                self.docked.remove(w)
                break

    def renameWindow(self, key):
        w = self.workspaceWindowByKey(key)

        x = QtWidgets.QDialog()
        h = QtWidgets.QVBoxLayout(x)
        form = QtWidgets.QFormLayout()
        h.addLayout(form)
        edit = QtWidgets.QLineEdit()
        edit.setText(w._docker_meta.title)
        form.addRow('&Title', edit)
        b = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel) 
        h.addWidget(b)
        b.accepted.connect(x.accept)
        b.rejected.connect(x.reject)
        x.show()
        if x.exec_() == QtWidgets.QDialog.Accepted:
            w._docker_meta.title = edit.text()

    def closeTab(self, index):
        self.workspace.removeTab(index)

    def tabsInWindowMenu(self, winmenu):
        actionlist = []
        for index in range(self.workspace.count()):
            child = self.workspace.widget(index)
            if index < 9:
                text = self.tr("&{0} {1}".format(index+1, child._docker_meta.title))
            else:
                text = self.tr("&{1}".format(child._docker_meta.title))

            action = winmenu.addAction(text)
            action.setCheckable(True)
            action.setChecked(child == self.workspace.currentWidget())
            action.triggered.connect(lambda *args, key=child._docker_meta.settingsKey: self.selectTab(key))

            actionlist.append(action)
        return actionlist

    def selectTab(self, settingsKey):
        desired = self.workspaceWindowByKey(settingsKey)
        if desired is not None:
            if hasattr(desired, '_docker'):
                desired._docker.show()
            else:
                self.workspace.setCurrentWidget(desired)
            return desired
        return None
