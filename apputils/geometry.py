import re
import json
import contextlib
import difflib
from PySide2 import QtCore, QtWidgets
from . import models

GLOBAL_FONT_MULTIPLIER = None


def get_font_multiplier():
    global GLOBAL_FONT_MULTIPLIER

    if GLOBAL_FONT_MULTIPLIER == None:
        import platform
        import ctypes

        if platform.system() == "Windows":
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            # print(user32.GetDC, gdi32.GetDeviceCaps)

            h = user32.GetDC(None)
            LOGPIXELSX = 88
            # LOGPIXELSY = 90
            # gdi32.GetDeviceCaps(h, LOGPIXELSX), gdi32.GetDeviceCaps(h, LOGPIXELSY)
            GLOBAL_FONT_MULTIPLIER = float(gdi32.GetDeviceCaps(h, LOGPIXELSX)) / 96.0
        else:
            GLOBAL_FONT_MULTIPLIER = 1.0
    return GLOBAL_FONT_MULTIPLIER


def get_char_width():
    return int(9.0 * get_font_multiplier())


def write_grid_geometry(grid, name):
    model = grid.model()
    settings = QtCore.QSettings()
    settings.beginGroup(name)
    header = (
        grid.horizontalHeader() if hasattr(grid, "horizontalHeader") else grid.header()
    )
    if isinstance(model, models.ObjectQtModel):
        # clear old reading
        keys = settings.childKeys()
        if "Column00" in settings.childKeys():
            for key in keys:
                if re.match("Column[0-9]{2}", key) != None:
                    settings.remove(key)

        for i, column in enumerate(model.columns):
            properties = {"width": header.sectionSize(i)}
            if column.hidden != header.isSectionHidden(i):
                properties["visible"] = not header.isSectionHidden(i)
            settings.setValue(f"column-{column.attr}", json.dumps(properties))

        if grid.isSortingEnabled():
            section = header.sortIndicatorSection()
            order = (
                "asc"
                if header.sortIndicatorOrder() == QtCore.Qt.AscendingOrder
                else "desc"
            )
            settings.setValue(
                "sort-column", json.dumps([model.columns[section].attr, order])
            )

        # Compare natural order with actual order
        natural = [c.attr for c in model.columns]
        actual = [None for c in model.columns]
        for i, column in enumerate(model.columns):
            actual[header.visualIndex(i)] = column.attr

        keys = settings.childKeys()
        for attr in natural + ["after#"]:
            if attr.endswith("#"):
                x = attr
            else:
                x = f"after-{attr}"
            if x in keys:
                settings.remove(x)

        match = difflib.SequenceMatcher(a=natural, b=actual)
        for op, i1, _, j1, j2 in match.get_opcodes():
            if op in ("insert", "replace"):
                if i1 == 0:
                    x = "after#"
                else:
                    x = f"after-{natural[i1 - 1]}"
                settings.setValue(x, json.dumps(actual[j1:j2]))
    else:
        for i in range(model.columnCount(QtCore.QModelIndex())):
            properties = {
                "width": header.sectionSize(i),
                "visible": not header.isSectionHidden(i),
                "visual-index": header.visualIndex(i),
            }
            settings.setValue(f"Column{i:02n}", json.dumps(properties))
    settings.endGroup()


def read_grid_geometry(grid, name):
    model = grid.model()
    settings = QtCore.QSettings()
    settings.beginGroup(name)
    total = sum(
        [grid.columnWidth(i) for i in range(model.columnCount(QtCore.QModelIndex()))]
    )
    defaults = None
    defaultTotal = None
    if hasattr(model, "columnWidthRatios"):
        defaults = model.columnWidthRatios()
        defaults = [defaults[i] for i in range(model.columnCount(QtCore.QModelIndex()))]
        if None not in defaults:
            defaultTotal = sum(defaults)
    header = (
        grid.horizontalHeader() if hasattr(grid, "horizontalHeader") else grid.header()
    )
    visuals = []
    if "Column00" in settings.childKeys():
        for i in range(model.columnCount(QtCore.QModelIndex())):
            p = settings.value(f"Column{i:02n}", None)
            if p == None:
                if defaults is not None and defaults[i] is not None:
                    grid.setColumnWidth(
                        i, int(float(defaults[i]) * total / defaultTotal)
                    )
            elif isinstance(p, int):
                grid.setColumnWidth(i, int(p))
            else:
                properties = json.loads(p)
                if properties["width"] > 0:
                    grid.setColumnWidth(i, properties["width"])
                if properties.get("visible", True):
                    header.showSection(i)
                else:
                    header.hideSection(i)
                visuals.append((i, properties["visual-index"]))
        if len(visuals) > 0:
            visuals.sort(key=lambda x: x[1])
            for logical, visible in visuals:
                header.moveSection(header.visualIndex(logical), visible)

        if grid.isSortingEnabled():
            # legacy default
            i = 0
            order = QtCore.Qt.AscendingOrder
            grid.sortByColumn(i, order)
    elif isinstance(model, models.ObjectQtModel):
        widthmult = get_char_width()
        for i, column in enumerate(model.columns):
            p = settings.value(f"column-{column.attr}", None)
            if p == None:
                if defaults is not None and defaults[i] is not None:
                    grid.setColumnWidth(
                        i, int(float(defaults[i]) * total / defaultTotal)
                    )
                elif hasattr(column, "char_width") and column.char_width != None:
                    grid.setColumnWidth(i, int(column.char_width * widthmult))
                if not column.hidden:
                    header.showSection(i)
                else:
                    header.hideSection(i)
            elif isinstance(p, int):
                grid.setColumnWidth(i, int(p))
            else:
                properties = json.loads(p)
                if properties["width"] > 0:
                    grid.setColumnWidth(i, properties["width"])
                if properties.get("visible", not column.hidden):
                    header.showSection(i)
                else:
                    header.hideSection(i)

        colmap = {column.attr: i for i, column in enumerate(model.columns)}

        if grid.isSortingEnabled():
            p = settings.value("sort-column", None)
            i, order = 0, QtCore.Qt.AscendingOrder
            if p != None:
                attr, direction = json.loads(p)
                if attr in colmap:
                    i = colmap[attr]
                    order = (
                        QtCore.Qt.AscendingOrder
                        if direction == "asc"
                        else QtCore.Qt.DescendingOrder
                    )
            grid.sortByColumn(i, order)

        natural = [c.attr for c in model.columns]
        for attr in natural + ["after#"]:
            if attr.endswith("#"):
                x = attr
            else:
                x = f"after-{attr}"
            p = settings.value(x, None)
            if p != None:
                # insert these columns after the other
                i = colmap[attr] if not attr.endswith("#") else -1
                columns = json.loads(p)
                base = -1 if i == -1 else header.visualIndex(i)
                for col in columns:
                    try:
                        i = colmap[col]
                    except KeyError:
                        continue
                    base += 1
                    header.moveSection(header.visualIndex(i), base)

    settings.endGroup()
    if getattr(model, "lockvert", False) and hasattr(grid, "resizeRowsToContents"):
        grid.resizeRowsToContents()


class TabMenuHolder:
    def __init__(self, tab):
        self.tab = tab

        self.actSaveLast = QtWidgets.QAction("&Reopen to last viewed tab", self.tab)
        self.actSaveLast.setCheckable(True)
        self.actSaveThis = QtWidgets.QAction("&Reopen to current tab", self.tab)
        self.actSaveThis.setCheckable(True)

        self.tab.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tab.customContextMenuRequested.connect(self.contextMenu)

    def contextMenu(self, pnt):
        tb = self.tab.tabBar()
        if tb.tabAt(pnt) == self.tab.currentIndex():
            self.menu = QtWidgets.QMenu()
            self.menu.addAction(self.actSaveLast)
            self.menu.addAction(self.actSaveThis)
            self.menu.popup(self.tab.mapToGlobal(pnt))

    def setChecks(self, status):
        self.actSaveLast.setChecked(status == WindowGeometry.TAB_REOPEN_LAST)
        self.actSaveThis.setChecked(status == WindowGeometry.TAB_REOPEN_SPECIFIED)


class WindowGeometry(QtCore.QObject):
    """
    This class saves and restores the size and other geometry artifacts about 
    the passed QWidget.  It hooks the closeEvent by attaching itself as an 
    eventFilter to the passed QWidget.

    Table header geometry should be saved by passing an extensionId to 
    :func:`TableView.setModel` at this point.  This may change in the future.

    The geometry is persisted with QSettings under a name that is determined 
    by one of the following (with first items taking precedence).  This name 
    is determined in __init__ and saved for writing the settings later under 
    the same name.
    
    * name parameter
    * widget.objectName()  (recommended)

    The QTabWidgets in the `tabs` list will have a context menu added on them 
    with options about how the tab selection should be recalled on reload.  They 
    can reopen the last opened, always reopen to a specific tab, or let it as 
    default (probably meaning the first tab is shown).

    :param widget: the QWidget for which to save & restore state
    :param name: optional identifier to associate this in the persistent state
    :param size: save & restore window size (default True)
    :param position: save & restore window position (default True)
    :param splitters: list of splitters to save position
    :param tabs: list of QTabWidgets whose tab selection should be managed/remembered
    :param grids: list of QTableView whose column widths should be remembered
    """

    TAB_REOPEN_DEFAULT = 0
    TAB_REOPEN_LAST = 1
    TAB_REOPEN_SPECIFIED = 2

    def __init__(
        self,
        widget,
        name=None,
        size=True,
        position=True,
        splitters=None,
        tabs=None,
        grids=None,
    ):
        QtCore.QObject.__init__(self, widget)

        self.widget = widget
        self.size = size
        self.position = position
        self.name = name
        if self.name is None:
            self.name = widget.objectName()
        self.splitters = splitters if splitters else []
        self.tabs = tabs if tabs else []
        self.tabs = [TabMenuHolder(t) for t in self.tabs]
        self.grids = grids if grids else []

        for s_index in range(len(self.splitters)):
            self.splitters[s_index].splitterMoved.connect(
                lambda pos, index, x=s_index: self.updateSplitter(x, pos, index)
            )

        for t_index in range(len(self.tabs)):
            self.tabs[t_index].tab.currentChanged.connect(
                lambda newSel, x=t_index: self.updateTab(x, newSel)
            )
            self.tabs[t_index].actSaveLast.toggled.connect(
                lambda checked, kind=self.TAB_REOPEN_LAST, x=t_index: self.updateTabLastSave(
                    x, checked, kind
                )
            )
            self.tabs[t_index].actSaveThis.toggled.connect(
                lambda checked, kind=self.TAB_REOPEN_SPECIFIED, x=t_index: self.updateTabLastSave(
                    x, checked, kind
                )
            )

        self.restoreState()

        if hasattr(self.widget, "finished"):
            self.widget.finished.connect(self.finished)
        else:
            self.widget.installEventFilter(self)

    def finished(self, i):
        self.saveState(splitters=False, tabs=False)

    def eventFilter(self, obj, event):
        # NOTE:  The getattr rather than a straight attribute dot access is
        # used to account for a presumed order-of-destruction bug.  There were
        # errors 'object has no attribute'.
        if obj is getattr(self, "widget", None) and event.type() == QtCore.QEvent.Close:
            self.saveState(splitters=False, tabs=False)
        return QtCore.QObject.eventFilter(self, obj, event)

    def saveState(self, splitters=True, tabs=True):
        """
        This saves the state of all controlled elements.  Some elements are 
        saved immediately when modified (such as splitters).  Thus we suppress 
        the state saving on close for these elements.

        :param splitters:  pass False to suppress the saving of the splitter 
            state for splitters passed in __init__
        :param tabs:  pass False to suppress the saving of the tab 
            state for tabs passed in __init__
        """
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        if self.size and self.position:
            settings.setValue("geometry", self.widget.saveGeometry())
        elif self.size:
            settings.setValue("size", self.widget.size())
        elif self.position:
            settings.setValue("pos", self.widget.pos())

        if hasattr(self.widget, "saveState"):
            # I'm probably a QMainWindow
            settings.setValue("windowState", self.widget.saveState())

        if splitters:
            for splitter_index in range(len(self.splitters)):
                settings.setValue(
                    self.splitter_persist_location(splitter_index),
                    self.splitters[splitter_index].saveState(),
                )

        if tabs:
            for tab_index in range(len(self.tabs)):
                settings.setValue(
                    self.tab_persist_location(tab_index, "to-reopen"),
                    self.tabs[tab_index].tab.currentIndex(),
                )

        for g in self.grids:
            self.grid_save(g)

        settings.endGroup()

    def restoreState(self):
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        if self.size and self.position:
            if settings.value("geometry") is not None:
                self.widget.restoreGeometry(settings.value("geometry"))
        elif self.size:
            if settings.value("size") is not None:
                self.widget.resize(settings.value("size"))
        elif self.position:
            if settings.value("pos") is not None:
                self.widget.move(settings.value("pos"))

        if hasattr(self.widget, "saveState"):
            # I'm probably a QMainWindow
            if settings.value("windowState") is not None:
                self.widget.restoreState(settings.value("windowState"))

        for g in self.grids:
            self.grid_restore(g)

        for splitter_index in range(len(self.splitters)):
            state = settings.value(self.splitter_persist_location(splitter_index))
            if state is not None:
                self.splitters[splitter_index].restoreState(state)

        for tab_index in range(len(self.tabs)):
            reopen = int(
                settings.value(
                    self.tab_persist_location(tab_index, "reopen-status"),
                    self.TAB_REOPEN_LAST,
                )
            )
            self.tabs[tab_index].setChecks(reopen)
            state = settings.value(self.tab_persist_location(tab_index, "to-reopen"))
            if state is not None and reopen != self.TAB_REOPEN_DEFAULT:
                self.tabs[tab_index].tab.setCurrentIndex(int(state))
        settings.endGroup()

    def save_xdata(self, name=None, **kwargs):
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        if name != None:
            settings.beginGroup(name)
        for k, v in kwargs.items():
            settings.setValue(k, v)

    def read_xdata(self, name=None):
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        if name != None:
            settings.beginGroup(name)
        return {k: settings.value(k) for k in settings.childKeys()}

    @contextlib.contextmanager
    def grid_reset(self, g):
        self.grid_save(g)
        yield
        self.grid_restore(g)

    def grid_restore(self, g):
        if g.model() != None:
            read_grid_geometry(g, f"{self.name}/{g.objectName()}")

    def grid_save(self, g):
        if g.model() != None:
            write_grid_geometry(g, f"{self.name}/{g.objectName()}")

    def splitter_persist_location(self, splitter_index):
        splitter_name = self.splitters[splitter_index].objectName()
        if splitter_name in [None, ""]:
            splitter_name = str(splitter_index)
        return f"splitter/{splitter_name}"

    def updateSplitter(self, splitter_index, pos, index):
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        settings.setValue(
            self.splitter_persist_location(splitter_index),
            self.splitters[splitter_index].saveState(),
        )
        settings.endGroup()

    def tab_persist_location(self, tab_index, v):
        tab_name = self.tabs[tab_index].tab.objectName()
        if tab_name in [None, ""]:
            tab_name = str(tab_index)
        return f"tab/{tab_name}/{v}"

    def updateTabLastSave(self, tab_index, checked, how):
        reopen = None
        tab_to_reopen = None
        if checked:
            reopen = how
            tab_to_reopen = self.tabs[tab_index].tab.currentIndex()
        else:
            reopen = self.TAB_REOPEN_DEFAULT

        if reopen is not None:
            self.tabs[tab_index].setChecks(reopen)

            settings = QtCore.QSettings()
            settings.beginGroup(self.name)
            settings.setValue(
                self.tab_persist_location(tab_index, "reopen-status"), reopen
            )
            if tab_to_reopen is not None:
                settings.setValue(
                    self.tab_persist_location(tab_index, "to-repen"), tab_to_reopen
                )
            settings.endGroup()

    def updateTab(self, tab_index, newSel):
        settings = QtCore.QSettings()
        settings.beginGroup(self.name)
        if (
            int(
                settings.value(
                    self.tab_persist_location(tab_index, "reopen-status"),
                    self.TAB_REOPEN_LAST,
                )
            )
            == self.TAB_REOPEN_LAST
        ):
            settings.setValue(
                self.tab_persist_location(tab_index, "to-reopen"),
                self.tabs[tab_index].tab.currentIndex(),
            )
        settings.endGroup()
