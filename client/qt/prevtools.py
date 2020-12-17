from PySide6 import QtCore, QtGui, QtWidgets

UI_ACTION_PAUSE = 150


class StdActionPause(QtCore.QTimer):
    def __init__(self, parent=None):
        super(StdActionPause, self).__init__(parent)
        self.setSingleShot(True)

    def ui_start(self):
        self.start(UI_ACTION_PAUSE)


class RevealedSplitterHandle(QtWidgets.QSplitterHandle):
    flickclick = QtCore.Signal()

    def __init__(self, orientation, parent=None):
        super(RevealedSplitterHandle, self).__init__(orientation, parent)

        self._font = QtGui.QFont("SansSerif", 10)

        self._image = QtGui.QIcon(":/fidolib/drag-left-arrow.png")
        self._btn1 = QtWidgets.QPushButton(self)
        self._btn1.setIcon(self._image)
        self._btn1.clicked.connect(self.flickclick.emit)
        self._btn2 = QtWidgets.QPushButton(self)
        self._btn2.setIcon(self._image)
        self._btn2.clicked.connect(self.flickclick.emit)

        self._btn1.hide()
        self._btn2.hide()

    def resizeEvent(self, event):
        r = self.rect()
        if r.width() > self.trig_width:
            width = r.width()
            width = (width - 24) // 2
            height = r.height()
            height = (height - 24) / 4

            r2 = r.adjusted(width, height, -width, -3 * height)
            self._btn1.setGeometry(r2)
            self._btn1.show()

            r2 = r.adjusted(width, 3 * height, -width, -height)
            self._btn2.setGeometry(r2)
            self._btn2.show()
        else:
            self._btn1.hide()
            self._btn2.hide()
        return super(RevealedSplitterHandle, self).resizeEvent(event)

    def paintEvent(self, event):
        r = self.rect()
        p = QtGui.QPainter()
        p.begin(self)

        if r.width() > self.trig_width:
            width = r.width()
            width = (width - 11) // 2
            height = r.height()
            height = (height - 16) / 4

            p.setFont(self._font)
            p.rotate(-90)
            r2 = r.adjusted(width, 2 * height - 10, -width, -2 * height + 10)
            p.drawText(-r2.bottom(), r2.right(), "Preview")
        p.end()


class RevealedSplitter(QtWidgets.QSplitter):
    def __init__(self, orientation, parent=None):
        super(RevealedSplitter, self).__init__(orientation, parent)

        self.thin_width = int(4.0)  # *apputils.get_font_multiplier())
        self.thick_width = int(30.0)  # *apputils.get_font_multiplier())
        self.trig_width = (self.thick_width + self.thin_width) // 2
        self.splitterMoved.connect(self.reset_width)

    def reset_width(self, pos, index):
        sizes = self.sizes()
        self.setHandleWidth(self.thick_width if sizes[-1] == 0 else self.thin_width)

    def show_preview(self):
        sizes = self.sizes()
        if sizes[-1] == 0:
            sizes[-2] -= 100
            sizes[-1] += 100
            self.setSizes(sizes)
            self.splitterMoved.emit(sizes[-2], len(sizes) - 2)
            self.reset_width(0, 0)

    def createHandle(self):
        x = RevealedSplitterHandle(self.orientation(), self)
        x.trig_width = self.trig_width
        x.flickclick.connect(self.show_preview)
        return x


class SidebarInterface:
    def __init__(self, fsession, exports_dir, parent=None):
        """start it up"""
        pass

    def set_report_keys(self, keys, prompts):
        """
        Orient the sidebar to this report with keys return of report from the
        server.  This is called once.
        """
        pass

    def highlight(self, row):
        """
        This is called with the highlighted row when it changes.
        """
        pass


class SidebarWrapper(QtWidgets.QMainWindow):
    def closeEvent(self, event):
        if self._libby != None and self.isVisible():
            self._libby.liberate_sidebar(by_close_button=True)
        return super(SidebarWrapper, self).closeEvent(event)


class SidebarLiberator(QtCore.QObject):
    def __init__(self, parent, sidebar, splitter):
        super(SidebarLiberator, self).__init__(parent)

        self.sidebar = sidebar
        self.splitter = splitter

        self._sidebar_lock = False
        self._wrapper = None

        if hasattr(self.sidebar, "toggle_liberated"):
            self.sidebar.toggle_liberated.connect(self.liberate_sidebar)

        self.sidebar_free_action = QtGui.QAction("&Liberate Sidebar", self)
        self.sidebar_free_action.setCheckable(True)
        self.sidebar_free_action.setShortcut("Ctrl+.")
        self.sidebar_free_action.triggered.connect(self.liberate_sidebar)
        parent.addAction(self.sidebar_free_action)
        sidebar.addAction(self.sidebar_free_action)

        if getattr(self.sidebar, "advance_highlight", None) != None:
            self.sidebar_advance_action = QtGui.QAction("&Advance Selection", self)
            self.sidebar_advance_action.setCheckable(True)
            self.sidebar_advance_action.setShortcut("F6")
            self.sidebar_advance_action.triggered.connect(
                self.sidebar.advance_highlight.emit
            )
            parent.addAction(self.sidebar_advance_action)
            sidebar.addAction(self.sidebar_advance_action)

    def setWindowTitle(self, title):
        self._title = title

    def setWindowIcon(self, icon):
        self._icon = icon

    def close(self):
        if self.liberated():
            self.liberate_sidebar()
        self.sidebar.close()

    def liberated(self):
        return self.sidebar not in [
            self.splitter.widget(i) for i in range(self.splitter.count())
        ]

    def liberate_sidebar(self, *args, by_close_button=False):
        if self._sidebar_lock:
            return

        if self.liberated():
            if self._wrapper != None:
                wrap = self._wrapper

                # save relative location of wrapper
                tr = self.parent().mapToGlobal(self.parent().rect().topRight())
                tl = wrap.frameGeometry().topLeft()
                self.parent().geo.save_xdata(
                    self.objectName(), locate=(tl - tr), size=wrap.size()
                )

                self.splitter.addWidget(self._wrapper.centralWidget())
                self._wrapper = None
                if not by_close_button:
                    self._sidebar_lock = True
                    wrap._preview = None
                    wrap.close()
                    self._sidebar_lock = False
        else:
            self._wrapper = SidebarWrapper()
            self._wrapper._libby = self
            self._wrapper.setWindowIcon(self._icon)
            self._wrapper.setWindowTitle(self._title)

            self._wrapper.setCentralWidget(self.sidebar)
            self._wrapper.show()

            # retrieve relative location of wrapper
            tr = self.parent().mapToGlobal(self.parent().rect().topRight())
            xdata = self.parent().geo.read_xdata(self.objectName())
            offset = xdata.get("locate", QtCore.QPoint(10, 0))
            self._wrapper.move(tr + offset)

            def_size = self.parent().size()
            def_size.setWidth(def_size.width() // 4 * 3)
            size = xdata.get("size", def_size)
            self._wrapper.resize(size)
