from QtShim import QtCore, QtWidgets
import apputils

class Binder(QtCore.QObject):
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

    def save_by_attr(self, attr):
        if self.loading:
            return
        if not self.widgets[attr].widgetModified():
            return
        try:
            v = self.widgets[attr].value()
        except apputils.UnknownKey:
            return
        setattr(self.bound, attr, v)
        self.widgets[attr].setWidgetModified(False)
        #uk = (something)[attr].url_key
        #if uk != None:
        #    setattr(self.bound, uk, self.widgets[attr].key_value())

    def bind(self, row, columns=None):
        if columns != None:
            colmap = {c.attr: c for c in columns}
            for attr, wdgt in self.widgets.items():
                if attr not in colmap:
                    continue
                col = colmap[attr]
                # See also apputils.widgets.views.ReportCoreModelDelegate.createEditor
                if isinstance(wdgt, QtWidgets.QLineEdit) and col.max_length != None:
                    wdgt.setMaxLength(col.max_length)

        self.load(row)
        self.bound = row

        if not self.connected:
            self.connected = True
            for attr, wdgt in self.widgets.items():
                wdgt.applyValue.connect(lambda a=attr: self.save_by_attr(a))

    def load(self, row):
        self.loading = True
        for attr, wdgt in self.widgets.items():
            wdgt.setValue(getattr(row, attr))
            wdgt.setWidgetModified(False)
        self.loading = False
        #    uk = (something)[attr].url_key
        #    if uk != None:
        #        wdgt.set_key_value(getattr(row, uk))

    def save(self, row):
        for attr, _ in self.widgets.items():
            self.save_by_attr(attr)
