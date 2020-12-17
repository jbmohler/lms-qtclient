from PySide6 import QtCore, QtWidgets
import valix
import apputils


class Binder(QtCore.QObject):
    values_loaded = QtCore.Signal(object)

    def __init__(self, parent):
        super(Binder, self).__init__(parent)

        self.widgets = {}
        self.loading = False
        self.bound = None
        self.connected = False

    def construct(self, attr, type_, **kwargs):
        w = apputils.construct(type_, **kwargs)
        self.widgets[attr] = w
        return w

    @property
    def attributes(self):
        return list(self.widgets.keys())

    def set_read_only(self, readonly=True):
        for attr, wdgt in self.widgets.items():
            wdgt.setReadOnly(readonly)

    def save_by_attr(self, attr):
        if self.loading:
            return
        if not self.widgets[attr].widgetModified():
            return
        v = self.widgets[attr].value()
        a2 = attr if "#" not in attr else attr[: attr.find("#")]
        setattr(self.bound, a2, v)
        self.widgets[attr].setWidgetModified(False)
        # uk = (something)[attr].url_key
        # if uk != None:
        #    setattr(self.bound, uk, self.widgets[attr].key_value())

    def safe_save(self, attr):
        try:
            self.save_by_attr(attr)
        except apputils.ModValueError:
            # control should be shown invalid
            pass

    def bind(self, row, columns=None, select_hack=False):
        if columns != None:
            colmap = {c.attr: c for c in columns}
            for attr, wdgt in self.widgets.items():
                a2 = attr if "#" not in attr else attr[: attr.find("#")]
                if a2 not in colmap:
                    continue
                col = colmap[a2]
                # See also apputils.widgets.views.ReportCoreModelDelegate.createEditor
                if isinstance(wdgt, QtWidgets.QLineEdit) and col.max_length != None:
                    wdgt.setMaxLength(col.max_length)

        self.load(row, select_hack=select_hack)
        self.bound = row

        if not self.connected:
            self.connected = True
            for attr, wdgt in self.widgets.items():
                wdgt.applyValue.connect(lambda a=attr: self.safe_save(a))

    def load(self, row, select_hack=False):
        self.loading = True
        if row == None:
            for attr, wdgt in self.widgets.items():
                wdgt.setValue(None)
                wdgt.setWidgetModified(False)
        else:
            for attr, wdgt in self.widgets.items():
                a2 = attr if "#" not in attr else attr[: attr.find("#")]
                try:
                    v = getattr(row, a2)
                except AttributeError:
                    ss = "QWidget{ background: --; }".replace(
                        "--", valix.BIND_ERROR_RGBA
                    )
                    wdgt.setStyleSheet(ss)
                    continue
                wdgt.setValue(v)
                if isinstance(wdgt, QtWidgets.QLineEdit) and select_hack:
                    wdgt.selectAll()
                wdgt.setWidgetModified(False)
        self.values_loaded.emit(row)
        self.loading = False
        #    uk = (something)[attr].url_key
        #    if uk != None:
        #        wdgt.set_key_value(getattr(row, uk))

    def reset_from_row(self, row, attr):
        self.loading = True
        try:
            for widattr, wdgt in self.widgets.items():
                # sigh, what good is a widget map if we must iterate anyhow
                a2 = widattr if "#" not in widattr else widattr[: widattr.find("#")]
                if a2 == attr:
                    wdgt.setValue(getattr(row, a2))
        finally:
            self.loading = False

    def save(self, row):
        for attr, _ in self.widgets.items():
            self.save_by_attr(attr)
