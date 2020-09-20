# -*- coding: utf-8 -*-
##############################################################################
#       Copyright (C) 2012, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################

import datetime
import fuzzyparsers
from PySide2 import QtCore, QtGui, QtWidgets
from apputils import ObjectQtModel, Column
from apputils.widgets import TableView

day_names = "Sunday Monday Tuesday Wednesday Thursday Friday Saturday".split(" ")

event_height = 20


class EventWrapper(object):
    """
    Structure for managing the individual items in a calendar view.  Note that
    the calendar has no more granularity than the day.

    These objects are likely created by the :class:`CalendarView`

    :param obj:  The object or some key of what is being represented in the calendar
    :param start_date:  The first date which the item should appear on the calendar
    :param end_date:  The last date for which the item should appear in the calendar
    :param text:  The text that should be shown on the calendar
    :param bkcolor:  something representing the background color of this item in
        the calendar
    """

    def __init__(self, obj, start_date, end_date, text, bkcolor):
        self.obj = obj
        self.start_date = start_date
        self.end_date = end_date
        self.text = text
        self.bkcolor = bkcolor
        self.visual_row_level = None


class CalendarRow(object):
    def __init__(self, day0_date, entries):
        assert (
            len(entries) == 7
        ), "We make a big assumption here that you have 7 days/week"
        self.day0_date = day0_date
        self.entries_by_day = entries
        for d in range(7):
            setattr(
                self, f"day{d}", f"{self.day0_date + datetime.timedelta(d)}",
            )

    def entryList(self, index):
        """
        :param index: is a QModelIndex and the return is a list of entries on
            this day.
        """
        return self.entries_by_day[index.column()]

    def entryBlock(self, entry, index, indexRect):
        this_day = self.date(index)
        r = indexRect
        r.setHeight(event_height - 2)
        if entry.start_date == this_day and entry.end_date == this_day:
            end_deflate = lambda x: x.adjusted(3, 0, -3, 0)
        elif entry.start_date == this_day:
            end_deflate = lambda x: x.adjusted(3, 0, 3, 0)
        elif entry.end_date == this_day:
            end_deflate = lambda x: x.adjusted(-3, 0, -3, 0)
        else:
            end_deflate = lambda x: x
        return end_deflate(r.translated(0, event_height * (entry.visual_row_level + 1)))

    def date(self, index):
        """
        :param index: is a QModelIndex and the return is the date of this cell
        """
        return self.day0_date + datetime.timedelta(index.column())


def rgb_contrasting_foreground(c):
    # see https://stackoverflow.com/questions/3116260/given-a-background-color-how-to-get-a-foreground-color-that-makes-it-readable-o
    consts = [0.2126, 0.7152, 0.0721]
    comps = [c.red(), c.green(), c.blue()]
    luminance = sum([c * x for c, x in zip(consts, comps)])
    cname = "white" if luminance < 140 else "black"
    return QtGui.QColor(cname)


class CalendarDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (
            QtWidgets.QApplication.style()
            if options.widget is None
            else options.widget.style()
        )

        options.text = ""
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, options, painter)

        painter.save()
        painter.translate(options.rect.topLeft())
        painter.setClipRect(options.rect.translated(-options.rect.topLeft()))

        this_day = index.internalPointer().date(index)

        # entry_back_color = options.palette.color(QtGui.QPalette.Highlight)

        deflated = lambda x: x.adjusted(2, 1, -2, -1)
        r = options.rect.translated(-options.rect.topLeft())
        r.setHeight(event_height - 2)
        painter.drawText(deflated(r), 0, f"{this_day.strftime('%B')} {this_day.day}")

        visible_count = (options.rect.height() // event_height) - 1
        entries = index.internalPointer().entryList(index)

        if len(entries) > visible_count:
            r = options.rect.translated(-options.rect.topLeft())
            r = r.translated(QtCore.QPoint(r.width() - 35, 0))
            r.setHeight(event_height - 2)
            painter.setPen(QtGui.QPen(QtGui.QColor("red")))
            painter.drawText(deflated(r), 0, "more")

        for entry in entries[:visible_count]:
            entry_back_color = entry.bkcolor
            entry_front_color = rgb_contrasting_foreground(entry_back_color)

            eventRect = index.internalPointer().entryBlock(
                entry, index, options.rect.translated(-options.rect.topLeft())
            )

            painter.setBrush(QtGui.QBrush(entry.bkcolor))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(eventRect)
            if entry.start_date == this_day or this_day.weekday() == 6:
                painter.setPen(QtGui.QPen(entry_front_color))
                painter.drawText(deflated(eventRect), 0, entry.text)

        painter.restore()

    def sizeHint(self, option, index):
        entries = index.internalPointer().entryList(index)
        return QtCore.QSize(80, (len(entries) + 1) * event_height + 1)


def test_calendar_entries():
    colors = "white, black, red, darkRed, green, darkGreen, blue, darkBlue, cyan, darkCyan, magenta, darkMagenta, yellow, darkYellow, gray, darkGray, lightGray".split(
        ", "
    )

    tests = []
    base = datetime.date(2012, 4, 15)
    for i, c in enumerate(colors):
        d = base + datetime.timedelta(days=i / 3)
        x = {"start": d, "end": d, "text": c, "bkcolor": QtGui.QColor(c)}
        tests.append(x)
    return tests


class CalendarView(TableView):
    """
    Clickable calendar view.

    >>> app = qtapp()
    >>> c = CalendarView()
    >>> c.setDateRange(datetime.date(2012, 3, 18), 6)
    >>> c.setEventList(test_calendar_entries()+[
    ...     {"start": datetime.date(2012, 3, 21), "end": datetime.date(2012, 3, 25), "text": "vacation"}, 
    ...     {"start": datetime.date(2012, 3, 28), "end": datetime.date(2012, 4, 4), "text": "nicer vacation"}, 
    ...     {"start": datetime.date(2012, 4, 9), "end": datetime.date(2012, 4, 9), "text": "wife birthday"}],
    ...     startDate = lambda x: x["start"],
    ...     endDate = lambda x: x["end"],
    ...     text = lambda x: x["text"],
    ...     bkColor = lambda x: x.get('bkcolor', QtGui.QColor(128, 128, 128)))
    """

    doubleClickCalendarEvent = QtCore.Signal(object)
    contextMenuCalendarEvent = QtCore.Signal(QtCore.QPoint, object)
    eventSelectionChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(CalendarView, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setItemDelegate(CalendarDelegate(self))
        self.firstDate = None
        self.numWeeks = None

    def setDateRange(self, firstDate, numWeeks, dayHeight=3):
        self.firstDate = firstDate
        self.numWeeks = numWeeks
        self.verticalHeader().setDefaultSectionSize(event_height * (dayHeight + 1) + 1)

    def setEventList(self, events, startDate, endDate, text, bkColor):
        events = [
            EventWrapper(e, startDate(e), endDate(e), text(e), bkColor(e))
            for e in events
        ]

        datarows = []
        for i in range(self.numWeeks):
            day0 = self.firstDate + datetime.timedelta(i * 7)
            day6 = self.firstDate + datetime.timedelta(i * 7 + 6)

            calWeek = []
            for i in range(7):
                d = day0 + datetime.timedelta(i)
                this_day_list = [
                    e for e in events if e.start_date <= d and e.end_date >= d
                ]
                calWeek.append(this_day_list)

                zz = list(range(len(this_day_list)))
                for e in this_day_list:
                    if e.visual_row_level in zz:
                        zz.remove(e.visual_row_level)
                for e in this_day_list:
                    if e.visual_row_level is None:
                        e.visual_row_level = zz[0]
                        del zz[0]

            datarows.append(CalendarRow(day0, calWeek))

        self.rows = ObjectQtModel(
            columns=[Column(f"day{d}", day_names[d]) for d in range(7)]
        )
        self.setModel(self.rows)
        self.rows.set_rows(datarows)
        self.selModel = self.selectionModel()
        self.selModel.selectionChanged.connect(self.selectionChanged)

    def selectionChanged(self, selected, deselected):
        self.eventSelectionChanged.emit()

    def selectedDates(self):
        m = self.selectionModel()
        if m is None:
            return []
        return [x.internalPointer().date(x) for x in m.selectedIndexes()]

    def selectDate(self, d, selMode=QtCore.QItemSelectionModel.Select):
        m = self.selectionModel()
        index = QtCore.QModelIndex()  # TODO:  write this code
        m.select(index, selMode)

    def itemAt(self, pos):
        index = self.indexAt(pos)
        if index is not None and index.isValid():
            for entry in index.internalPointer().entryList(index):
                eventRect = index.internalPointer().entryBlock(
                    entry, index, self.visualRect(index)
                )
                if eventRect.contains(pos):
                    return entry.obj
        return None

    def mouseDoubleClickEvent(self, event):
        obj = self.itemAt(event.pos())
        if obj is not None:
            self.doubleClickCalendarEvent.emit(obj)
            event.accept()
        super(CalendarView, self).mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        obj = self.itemAt(event.pos())
        if obj is not None:
            self.contextMenuCalendarEvent.emit(event.pos(), obj)
            event.accept()
        super(CalendarView, self).contextMenuEvent(event)


def laywid(lay, wid):
    lay.addWidget(wid)
    return wid


class CalendarTopNav(QtWidgets.QWidget):
    """
    >>> app = qtapp()
    >>> c = CalendarTopNav()
    """

    relativeMove = QtCore.Signal(int)
    absoluteMove = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(CalendarTopNav, self).__init__(parent)

        main = QtWidgets.QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        self.earlier = [
            laywid(main, QtWidgets.QPushButton("<<<")),
            laywid(main, QtWidgets.QPushButton("<<")),
            laywid(main, QtWidgets.QPushButton("<")),
        ]
        self.earlier.reverse()
        self.month_label = laywid(main, QtWidgets.QLabel("&Month:"))
        self.month = laywid(main, QtWidgets.QLineEdit())
        self.later = [
            laywid(main, QtWidgets.QPushButton(">")),
            laywid(main, QtWidgets.QPushButton(">>")),
            laywid(main, QtWidgets.QPushButton(">>>")),
        ]
        for b in self.earlier + self.later:
            b.setMaximumWidth(40)
        self.month_label.setBuddy(self.month)
        self.month.returnPressed.connect(self.input_reset)
        self.setFocusProxy(self.month)
        self.setMaximumHeight(self.month.sizeHint().height())

        for i in range(3):
            # need to fancy-dance the callables to get the correct closure in
            # the face of ambiguious Qt signal parameters.
            _earlier = lambda *args, index=-i - 1: self.relativeMove.emit(index)
            _later = lambda *args, index=+i + 1: self.relativeMove.emit(index)
            self.earlier[i].clicked.connect(_earlier)
            self.later[i].clicked.connect(_later)

    def input_reset(self):
        try:
            x = fuzzyparsers.parse_date(self.month.text())
            self.absoluteMove.emit(x)
        except Exception as e:
            pass
