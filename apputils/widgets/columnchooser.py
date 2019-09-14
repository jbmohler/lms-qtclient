from QtShim import QtCore, QtWidgets
import rtlib
import apputils

class ColumnDefnMixin:
    @property
    def visual_index(self):
        return not self.mothership_header.visibleIndexAt(self.logical)

    @property
    def visible(self):
        return not self.mothership_header.isSectionHidden(self.logical)

    @visible.setter
    def visible(self, value):
        if value:
            self.mothership_header.showSection(self.logical)
        else:
            self.mothership_header.hideSection(self.logical)

ColumnDefn = rtlib.fixedrecord('ColumnDefn', ['logical', 'attr', 'label'], mixin=ColumnDefnMixin)

class MyDroppingModel(apputils.ObjectQtModel):
    column_move = QtCore.Signal(str, int, int)

    def flags(self, index):
        d = super(MyDroppingModel, self).flags(index)
        return d | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeTypes(self):
        return ['application/x-attributes']

    def mimeData(self, indexes):
        x = QtCore.QMimeData()
        x.setData('application/x-attributes', indexes[0].data(apputils.ObjectRole).attr)
        return x

    def dropMimeData(self, data, action, row, column, parent):
        attr = data.data('application/x-attributes')
        # complicated dance of deletions & insertions ... TODO preserve selection elegantly
        index, column = [(i, c) for i, c in enumerate(self.rows) if c.attr == attr][0]
        self.column_move.emit(attr, index, parent.row())
        if parent.isValid():
            self.rows.insert(parent.row(), column)
            if parent.row() < index:
                index += 1
        else:
            self.rows.append(column)
        del self.rows[index]
        self.set_rows(self.rows)
        return True


class ModelColumnChooser(QtWidgets.QDialog):
    def __init__(self, parent):
        super(ModelColumnChooser, self).__init__(parent)

        self.setWindowTitle('Manage Columns')

        # delayed for recursion control
        from . import views

        # setup widgets
        self.layout = QtWidgets.QVBoxLayout(self)
        self.body = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.body)

        self.grid = views.TableView(column_choosing=False)
        self.grid.setSelectionBehavior(self.grid.SelectRows)
        self.grid.setSelectionMode(self.grid.SingleSelection)
        self.grid.setDragDropMode(self.grid.InternalMove)
        self.grid.setDragEnabled(True)
        self.grid.viewport().setAcceptDrops(True)
        self.grid.verticalHeader().setDefaultSectionSize(18)
        columns = [\
                apputils.field('label', 'Label', check_attr='visible'),
                apputils.field('attr', 'Attribute')]
        self.model = MyDroppingModel(columns)
        self.model.column_move.connect(self.column_move)
        self.grid.setModel(self.model)
        self.grid.horizontalHeader().hideSection(1)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self.body.addWidget(self.grid)

        self.layout.addWidget(QtWidgets.QLabel('Drag to change order'))

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QDB.Close, QtCore.Qt.Horizontal)
        self.buttons.rejected.connect(self.close)
        self.layout.addWidget(self.buttons)

    def set_view(self, view):
        self._view = view
        ColumnDefn.mothership_header = self._view.header()
        CD = lambda index, c: ColumnDefn(logical=index, attr=c.attr, label=c.label.replace('\n', ' '))
        colmodel = apputils.base_columned_model(self._view.model())
        self.rows = [CD(index, c) for index, c in enumerate(colmodel.columns)]
        self.rows.sort(key=lambda x: self._view.header().visualIndex(x.logical))
        self.model.set_rows(self.rows)
        self.grid.resizeColumnsToContents()

    def column_move(self, attr, old_visual, new_visual):
        if old_visual < new_visual:
            new_visual -= 1
        elif new_visual == -1:
            h = self._view.header()
            x = [h.visualIndex(index) for index in range(self._view.model().columnCount(QtCore.QModelIndex()))]
            new_visual = max(x)
        self._view.header().moveSection(old_visual, new_visual)
