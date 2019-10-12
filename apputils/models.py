import contextlib
import decimal
import itertools
import valix
from rtlib import Column, field, ModelMixin
from PySide2 import QtCore, QtGui

def base_columned_model(m1):
    if isinstance(m1, QtCore.QAbstractProxyModel):
        m1 = m1.sourceModel()
    if isinstance(m1, ObjectQtModel):
        return m1
    else:
        return None

class ValueSetRefusal(ValueError):
    pass

HILITE_BK_COLOR = '#ecf469'

ObjectRole = QtCore.Qt.UserRole+1
ColumnAttributeRole = QtCore.Qt.UserRole+2
ColumnMetaRole = QtCore.Qt.UserRole+3
UrlRole = QtCore.Qt.UserRole+4
DecimalRole = QtCore.Qt.UserRole+5
RenderRole = QtCore.Qt.UserRole+6

RenderNormal = None
RenderHtml = 1
RenderMultiline = 2

class ObjectQtModel(QtCore.QAbstractItemModel):
    def __init__(self, columns, rowprops=None, parent=None, descendant_attr=None, dataclass=None):
        # TODO: address TieredObjectQtModel duplicate
        super(ObjectQtModel, self).__init__(parent)
        ModelMixin.__init__(self, columns, rowprops)
        self.descendant_attr = descendant_attr
        self._mass_proxies = None
        self._hilite = None
        self.parent_map = {}

        try:
            # rather ham-fisted approach to locking stuff to top of cells automatically
            self.lockvert = len([c for c in self.columns if c.type_ in ('multiline', 'html')]) > 0
        except:
            # rather ham-fisted hack in ham-fisted algorithm to fallback to default
            self.lockvert = False

        self._main_rows = None # live rows
        self._flip_rows = None # flipper rows before edit
        self._fltr_rows = None # currently showing rows (not including flipper)

        if dataclass == None:
            self.constraint_functions = []
        else:
            self.constraint_functions = valix.class_constraints(dataclass)
        self.invalid_fields = set()

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.columns[col].label
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return str(col+1)
        return None

    def sort(self, column, order):
        if self._main_rows == None:
            return
        usemain = self._fltr_rows == None
        if usemain:
            sortlist = self._main_rows[:]
        else:
            sortlist = self._fltr_rows[:]
        c = self.columns[column]
        sortlist.sort(key=lambda x: c.sortkey(getattr(x, c.attr)), reverse=order == QtCore.Qt.DescendingOrder)
        self.beginResetModel()
        if usemain:
            self._main_rows = sortlist
        else:
            self._fltr_rows = sortlist
        self.endResetModel()

    def removeRows(self, row, count, parent):
        assert not parent.isValid(), 'hierarchical models not supported here (yet)'

        self.beginRemoveRows(parent, row, row+count-1)
        holder = self._main_rows if self._fltr_rows == None else self._fltr_rows
        todel = holder[row:row+count]
        del holder[row:row+count]
        if self._fltr_rows != None:
            for row in todel:
                if row in self._main_rows:
                    self._main_rows.remove(row)
        self.endRemoveRows()
        return True

    def set_rows(self, rows, flipper=None):
        self.invalid_fields = set()
        self.beginResetModel()
        self._main_rows = rows
        if flipper != None:
            self._flip_rows = [flipper]
        else:
            self._flip_rows = None
        self.endResetModel()

    def append_row(self, row):
        holder = self._main_rows if self._fltr_rows == None else self._fltr_rows
        rowc = len(holder)
        self.beginInsertRows(QtCore.QModelIndex(), rowc, rowc)
        holder.append(row)
        if self._fltr_rows != None:
            self._main_rows.append(row)
        self.endInsertRows()

    def promote_flipper(self, row, flipper=None):
        assert row in self._flip_rows

        holder = self._main_rows if self._fltr_rows == None else self._fltr_rows
        holder.append(row)
        if self._fltr_rows != None:
            self._main_rows.append(row)
        self._flip_rows.remove(row)
        if flipper != None:
            rowc = len(holder)
            self.beginInsertRows(QtCore.QModelIndex(), rowc, rowc)
            self._flip_rows.append(flipper)
            self.endInsertRows()

    def is_flipper(self, row):
        return self._flip_rows != None and row in self._flip_rows

    @property
    def rows(self):
        # always return _main_rows (with-out flipper)
        holder = self._main_rows
        result = holder[:]
        if self._flip_rows != None:
            result += self._flip_rows
        return result

    def set_highlight_string(self, hilite):
        self._hilite = hilite
        self.data_changed_all()

    def data_changed_all(self):
        invalid = QtCore.QModelIndex()
        i1 = self.index(0, 0, invalid)
        i2 = self.index(self.rowCount(invalid), self.columnCount(invalid), invalid)
        self.dataChanged.emit(i1, i2)

    def filter_by_predicate(self, pred):
        filter = [row for row in self._main_rows if pred(row)]
        self.beginResetModel()
        self._fltr_rows = filter
        self.endResetModel()

    def unfilter(self):
        self.beginResetModel()
        self._fltr_rows = None
        self.endResetModel()

    def columnCount(self, parent):
        # columns are assumed to be the same for all parents
        return len(self.columns)

    def get_index_child_list(self, parent):
        if parent is None:
            parent = QtCore.QModelIndex()
        row = self.row_object_by_index(parent)
        if row is None:
            base = self._main_rows if self._fltr_rows == None else self._fltr_rows
            if self._flip_rows != None:
                base = base[:] + self._flip_rows
            return base
        elif self.descendant_attr == None:
            return None
        else:
            return getattr(row, self.descendant_attr)

    def rowCount(self, parent):
        children = self.get_index_child_list(parent)
        if children == None:
            return 0
        return len(children)

    def index(self, row, column, parent):
        children = self.get_index_child_list(parent)
        if children == None:
            return QtCore.QModelIndex()
        if 0 <= row < len(children):
            k = children[row]
            self.parent_map[id(k)] = parent
        else:
            k = None
        return self.createIndex(row, column, k)

    def parent(self, child):
        obj = self.row_object_by_index(child)
        index = QtCore.QModelIndex()
        if id(obj) in self.parent_map:
            b = self.parent_map[id(obj)]
            if b != None:
                index = b
        return index

    def row_object_by_index(self, index):
        return index.internalPointer()

    def object_changed(self, obj):
        self.dataChanged.emit(*self.index_object(obj))

    def index_object_column(self, obj, column):
        try:
            holder = self._main_rows if self._fltr_rows == None else self._fltr_rows
            if holder == None:
                raise ValueError('not yet initialized with rows')
            rowindex = holder.index(obj)
        except ValueError:
            return QtCore.QModelIndex()

        for b, c in enumerate(self.columns):
            if c.attr == column:
                colindex = b
                break
        else:
            return QtCore.QModelIndex()
        return self.index(rowindex, colindex, QtCore.QModelIndex())

    def index_row(self, row):
        parent = QtCore.QModelIndex()
        if row > self.rowCount(parent) or row < 0:
            return QtCore.QModelIndex(), QtCore.QModelIndex()
        return self.index(row, 0, parent), self.index(row, len(self.columns)-1, parent)

    def index_object(self, obj, parent=None):
        try:
            holder = self._main_rows if self._fltr_rows == None else self._fltr_rows
            row = holder.index(obj)
        except ValueError:
            return QtCore.QModelIndex(), QtCore.QModelIndex()
        return self.index(row, 0, parent), self.index(row, len(self.columns)-1, parent)

    def index_columns(self, column, parent=None):
        colindex = None
        for index, c in enumerate(self.columns):
            if c.attr == column:
                colindex = index
        if colindex == None:
            return
        count = self.rowCount(parent)
        if count > 0:
            return self.index(0, colindex, parent), self.index(count-1, colindex, parent)
        else:
            return QtCore.QModelIndex(), QtCore.QModelIndex()

    @contextlib.contextmanager
    def massEditProxies(self, indices):
        self._mass_proxies = indices
        yield
        self._mass_proxies = None

    def _column_at_index(self, index):
        if not 0 <= index.column() < len(self.columns):
            return None
        return self.columns[index.column()]

    def data(self, index, role):
        if not index.isValid():
            return None

        r = self.row_object_by_index(index)
        if role == ObjectRole:
            return r

        c = self._column_at_index(index)
        if c == None:
            return None
        if role == ColumnMetaRole:
            return c
        if role == ColumnAttributeRole:
            return c.attr

        primary_value = getattr(r, c.attr)

        if role == QtCore.Qt.DisplayRole:
            if c.checkbox:
                return None
            func = c.formatter
            if primary_value == None and not getattr(func, 'allow_none', False):
                return None
            return func(primary_value)
        elif role == QtCore.Qt.EditRole:
            if c.checkbox:
                return None
            return primary_value
        elif role == QtCore.Qt.CheckStateRole:
            if c.checkbox:
                return QtCore.Qt.Checked if primary_value else QtCore.Qt.Unchecked
            elif c.check_attr != None:
                return QtCore.Qt.Checked if getattr(r, c.check_attr) else QtCore.Qt.Unchecked
        elif role == QtCore.Qt.TextAlignmentRole:
            align = c.alignment
            hori = "left"
            vert = "top" if self.lockvert else "vcenter"
            if align is not None:
                t = align.split('-', 1)
                if len(t) == 1:
                    hori = align
                else:
                    hori, vert = t
            # should not have to cast to int in either of these returns
            # see https://bugreports.qt-project.org/browse/PYSIDE-20
        #     if hasattr(r,"textAlignmentRole"):
        #         return int(r.textAlignmentRole(c))
            return int({"left": QtCore.Qt.AlignLeft, "hcenter": QtCore.Qt.AlignHCenter, "right": QtCore.Qt.AlignRight}[hori] | \
                     {"top": QtCore.Qt.AlignTop, "vcenter": QtCore.Qt.AlignVCenter, "bottom": QtCore.Qt.AlignBottom}[vert])
        # elif role == QtCore.Qt.FontRole:
        #     if hasattr(r,"fontRole"):
        #         # return r.fontRole(c)
        elif role == QtCore.Qt.SizeHintRole:
            return QtCore.QSize(150, 24)
        elif role == QtCore.Qt.ForegroundRole:
            if c.foreground_attr != None:
                v = getattr(r, c.foreground_attr)
                return QtGui.QColor(v)
            if 'foreground' in self.rowprops:
                v = getattr(r, self.rowprops['foreground'])
                return QtGui.QColor(v)
        elif role == QtCore.Qt.BackgroundRole:
            if self._hilite != None and primary_value != None:
                t = c.formatter(primary_value)
                s = self._hilite.lower()
                if t != None and t.lower().find(s) >= 0:
                    return QtGui.QColor(HILITE_BK_COLOR)
            if (id(r), c.attr) in self.invalid_fields:
                return QtGui.QColor(valix.INVALID_COLOR)
            if c.background_attr != None:
                v = getattr(r, c.background_attr)
                return QtGui.QColor(v)
            if 'background' in self.rowprops:
                v = getattr(r, self.rowprops['background'])
                return QtGui.QColor(v)
        # elif role >= QtCore.Qt.UserRole:
        #     assert QtCore.Qt.UserRole <= role < QtCore.Qt.UserRole+len(self.columns)
        #     roles = self.roleNames()
        #     c = self.columns[role - QtCore.Qt.UserRole]
        #     return toQType(primary_value,suggested=primary_type)
        elif role == UrlRole:
            if c.url_factory == None:
                return None
            return c.url_factory(primary_value)
        elif role == DecimalRole:
            if c.is_numeric and primary_value != None:
                # TODO:  find a better way to get decimals
                if c.type_ == 'currency_usd':
                    return decimal.Decimal(primary_value).quantize(decimal.Decimal('.01'))
                else:
                    return decimal.Decimal(primary_value).quantize(decimal.Decimal('.01'))
            else:
                return None
        elif role == RenderRole:
            if c.type_ == 'html':
                return RenderHtml
            if c.type_ == 'multiline':
                return RenderMultiline
            return RenderNormal

        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return None
        #elif role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            #return None

        c = self._column_at_index(index)

        attr = c.attr
        if c.check_attr and role == QtCore.Qt.CheckStateRole:
            value = value == QtCore.Qt.Checked
            attr = c.check_attr
        elif c.checkbox and role == QtCore.Qt.CheckStateRole:
            value = value == QtCore.Qt.Checked

        if role == QtCore.Qt.EditRole:
            value = c.coerce_edit(value)

        self._values_to_check = []

        if self._mass_proxies == None:
            r = self.row_object_by_index(index)
            setattr(r, attr, value)
            self.dataChanged.emit(index, index)
        else:
            # TODO:  assert that all proxy indices are in the same column and
            # have the same parent.
            minindex, maxindex = index, index
            for pin in self._mass_proxies:
                r = self.row_object_by_index(pin)
                setattr(r, attr, value)
                if pin.row() < minindex.row():
                    minindex = pin
                if pin.row() > maxindex.row():
                    maxindex = pin
            self.dataChanged.emit(minindex, maxindex)

        # add siblings of values to check to list of values to check
        self._values_to_check.sort(key=lambda x: id(x[0]))
        v2 = []
        for idrow, cells in itertools.groupby(self._values_to_check, key=(lambda x: id(x[0]))):
            clist = list(cells)
            attrs = set([at1 for row, at1 in clist])
            row = clist[0][0]
            for idrow2, at1 in self.invalid_fields:
                if idrow2 == idrow:
                    attrs.add(at1)
            for at1 in attrs:
                v2.append((row, at1))

        valids, invalids = valix.validate_cellset(self.constraint_functions, v2)
        self.update_invalid_fields(valids, invalids)

        del self._values_to_check

        return True

    def append_change_value(self, row, attr):
        if not hasattr(self, '_values_to_check'):
            # drop it on the floor
            return
        self._values_to_check.append((row, attr))

    def update_invalid_fields(self, valids, invalids):
        v2 = [(id(row), attr) for row, attr in valids]
        iv2 = [(id(row), attr) for row, attr, _ in invalids]
        self.invalid_fields.difference_update(v2)
        self.invalid_fields.update(iv2)

    def flags(self, index):
        c = self._column_at_index(index)
        if c == None:
            return 0
        result = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if c.check_attr != None:
            result |= QtCore.Qt.ItemIsUserCheckable
        if c.editable:
            if c.checkbox:
                result |= QtCore.Qt.ItemIsUserCheckable
            else:
                result |= QtCore.Qt.ItemIsEditable
        return result


class TieredObjectQtModel(ObjectQtModel):
    def __init__(self, columns, dataclasses, rowprops=None, parent=None, descendant_attr=None):
        # TODO:  address ObjectQtModel duplicate
        super(TieredObjectQtModel, self).__init__(parent)
        ModelMixin.__init__(self, columns, rowprops)
        self.descendant_attr = descendant_attr
        self._mass_proxies = None
        self.parent_map = {}

        self.dataclasses = dataclasses

        self.constraint_functions = []
        #if dataclass == None:
        #    self.constraint_functions = []
        #else:
        #    self.constraint_functions = valix.class_constraints(dataclass)
        self.invalid_fields = set()

    @property
    def exportcolumns(self):
        return self.dataclasses[0].model_columns

    def _column_at_index(self, index):
        row = self.row_object_by_index(index)

        attr = self.columns[index.column()].attr
        try:
            return row.__class__.model_columns[attr]
        except:
            return None
