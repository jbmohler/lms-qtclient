import sys
import math
import concurrent.futures as futures
from PySide6 import QtCore, QtGui, QtWidgets


class BackgrounderShell(object):
    def __init__(self, bgdisplay):
        self.bgdisplay = bgdisplay

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if hasattr(self.bgdisplay, "terminated"):
            self.bgdisplay.terminated(args[0])

    def wait_futures(self, future_list):
        not_done = future_list
        while len(not_done) > 0:
            _, not_done = futures.wait(not_done, 0.01)
            if hasattr(self.bgdisplay, "continuing"):
                self.bgdisplay.continuing()
            self.processEvents()

    def as_completed(self, future_list):
        not_done = future_list
        while len(not_done) > 0:
            done, not_done = futures.wait(not_done, 0.01)
            for f in done:
                yield f
            self.processEvents()

    def background(self, func, *args, **kwargs):
        executor = futures.ThreadPoolExecutor(1)
        f1 = executor.submit(func, *args, **kwargs)
        self.wait_futures([f1])
        return f1.result()

    def processEvents(self):
        QtCore.QCoreApplication.instance().processEvents()


def animator(parent):
    return BackgrounderShell(AnimateWait(parent))


def wait_cursor(parent):
    return BackgrounderShell(ObscuringWaitCursor(parent))


class Progress(QtWidgets.QProgressDialog):
    def __enter__(self):
        # Qt default of pausing 4 seconds gets bizarre
        self.setMinimumDuration(0)
        self.setModal(True)
        self.show()
        return self

    def __exit__(self, *args):
        self.close()

    def wait_futures(self, future_list):
        not_done = future_list
        while len(not_done) > 0:
            _, not_done = futures.wait(not_done, 0.01)
            self.processEvents()

    def as_completed(self, future_list):
        not_done = future_list
        while len(not_done) > 0:
            done, not_done = futures.wait(not_done, 0.01)
            for f in done:
                yield f
            self.processEvents()

    def background(self, func, *args, **kwargs):
        executor = futures.ThreadPoolExecutor(1)
        f1 = executor.submit(func, *args, **kwargs)
        self.wait_futures([f1])
        return f1.result()

    def processEvents(self):
        QtCore.QCoreApplication.instance().processEvents()


def progress(parent, msg, minv=0, maxv=0):
    p = Progress(msg, None, minv, maxv, parent)
    if parent != None:
        p.setWindowModality(QtCore.Qt.WindowModal)
    name = QtWidgets.QApplication.applicationName()
    p.setWindowTitle(name)
    return p


class JointBackgrounder:
    def __init__(self, *args):
        self.backgrounders = args

    def continuing(self, *args, **kwargs):
        for b in self.backgrounders:
            if hasattr(b, "continuing"):
                b.continuing(*args, **kwargs)

    def complete(self, *args, **kwargs):
        for b in self.backgrounders:
            if hasattr(b, "complete"):
                b.complete(*args, **kwargs)

    def terminated(self, *args, **kwargs):
        for b in self.backgrounders:
            if hasattr(b, "terminated"):
                b.terminated(*args, **kwargs)


class AnimateWait(QtWidgets.QWidget):
    def __init__(self, obscured):
        super(AnimateWait, self).__init__(obscured)

        # resize to match parent
        # print(parent.geometry())
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        # self.setWindowFlags(QtCore.Qt.Popup)
        # self.setWindowOpacity(.25)

        self.obscured = obscured

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.cycle)
        self.timer.start()

        self.clock = 0

        self.term_closed = False
        QtCore.QTimer.singleShot(250, self.show_first)

        self.arcstart = 90 * 16

    def show_first(self):
        if self.term_closed:
            return
        self.obscured.installEventFilter(self)

        self.move(QtCore.QPoint(0, 0))
        self.resize(self.obscured.size())
        self.show()

    def eventFilter(self, obj, ev):
        if obj == self.obscured and ev.type() == QtCore.QEvent.Resize:
            self.resize(self.obscured.size())
            self.show()
        return False

    def cycle(self):
        self.clock += 1
        self.arcstart = (self.arcstart - 32) % 5760
        self.update()

    def paintEvent(self, event):
        # show spinning ball
        p = QtGui.QPainter()
        p.begin(self)

        x = self.rect()
        c = QtGui.QColor("gray")
        c.setAlpha(90)
        p.fillRect(x, c)

        radfac = (0.9 - 0.1) * math.atan(self.clock / 100) / math.pi * 2
        radius = int(float(min(x.width(), x.height())) * radfac * 0.5)
        center = x.center()
        arc_rect = QtCore.QRect(
            center.x() - radius, center.y() - radius, 2 * radius, 2 * radius
        )

        c = QtGui.QColor("blue")
        c.setAlpha(40)
        arc_brush = QtGui.QBrush(c)
        for factor in range(7):
            p.setPen(
                QtGui.QPen(
                    arc_brush,
                    radius // (5 + factor),
                    QtCore.Qt.SolidLine,
                    QtCore.Qt.RoundCap,
                )
            )
            p.drawArc(arc_rect, self.arcstart + (45 * factor * 16), -30 * 16)
        p.end()

    def terminated(self, exception):
        self.term_closed = True
        self.obscured.removeEventFilter(self)
        self.timer.stop()
        self.hide()
        self.close()


class ObscuringWaitCursor(QtWidgets.QWidget):
    def __init__(self, obscured):
        super(ObscuringWaitCursor, self).__init__(obscured)

        # resize to match parent
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.obscured = obscured
        self.obscured.setCursor(QtCore.Qt.WaitCursor)
        self.setCursor(QtCore.Qt.WaitCursor)
        self.term_closed = False

        self.show_first()

    def show_first(self):
        self.obscured.installEventFilter(self)

        self.move(QtCore.QPoint(0, 0))
        self.resize(self.obscured.size())
        self.show()

    def eventFilter(self, obj, ev):
        if obj == self.obscured and ev.type() == QtCore.QEvent.Resize:
            self.resize(self.obscured.size())
            self.show()
        return False

    def terminated(self, exception):
        self.term_closed = True
        self.obscured.removeEventFilter(self)
        self.hide()
        self.close()

        self.obscured.unsetCursor()
        self.unsetCursor()


class BackgrounderAbort(Exception):
    pass


class BackgrounderNamedJob:
    def __init__(self, bg, name):
        self.bg = bg
        self.name = name
        self.invocation = None

    def cancel(self):
        if self.invocation != None:
            self.invocation.cancel()
            self.invocation = None

    def __call__(self, *args, **kwargs):
        if self.invocation != None:
            self.invocation.cancel()
            self.invocation = None

        self.invocation = self.bg(*args, **kwargs)
        return self.invocation


class BackgrounderNamedJobManager:
    def __init__(self, bg):
        self.bg = bg

    def __getitem__(self, index):
        if index not in self.bg.named_jobs:
            self.bg.named_jobs[index] = BackgrounderNamedJob(self.bg, index)
        return self.bg.named_jobs[index]


class Backgrounder(QtCore.QObject):
    def __init__(self, parent, cadence=15, threads=4):
        super(Backgrounder, self).__init__(parent)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(cadence)
        self.timer.timeout.connect(self.check_futures)

        self.executor = futures.ThreadPoolExecutor(threads)
        self.futures = []
        self.named_jobs = {}
        self.named_job_manager = BackgrounderNamedJobManager(self)

        self._aborted = False

        self.delayed_waiting = []

    def __call__(self, callbacks, call, *args, **kwargs):
        myfuture = None
        if hasattr(call, "future_invocation"):
            myfuture, call = call.future_invocation()
        f1 = self.executor.submit(call, *args, **kwargs)
        f1._gen = callbacks()
        f1._status_callbacks = next(f1._gen)
        f1._invfuture = myfuture
        self.futures.append(f1)
        if not self.timer.isActive():
            self.timer.start()
        return myfuture

    @property
    def named(self):
        return self.named_job_manager

    def delayed(self, delay, callbacks, call, *args, **kwargs):
        g = callbacks()
        cb2 = next(g)
        delaystruct = {
            "gen": g,
            "status_callbacks": cb2,
            "call": call,
            "args": args,
            "kwargs": kwargs,
        }
        self.delayed_waiting.append(delaystruct)

        QtCore.QTimer.singleShot(delay, lambda d=delaystruct: self.delay_done(d))

    def cancel_pending(self):
        for f in reversed(self.futures):
            if not f.cancel():
                if f._invfuture != None:
                    f._invfuture.cancel()

    def abort(self):
        self.cancel_pending()
        self._aborted = True

    def delay_done(self, delay):
        self.delayed_waiting.remove(delay)

        call, args, kwargs = delay["call"], delay["args"], delay["kwargs"]

        f1 = self.executor.submit(call, *args, **kwargs)
        f1._gen = delay["gen"]
        f1._status_callbacks = delay["status_callbacks"]
        self.futures.append(f1)
        if not self.timer.isActive():
            self.timer.start()

    def check_futures(self):
        done, not_done = futures.wait(self.futures, 0.01)
        self.futures = list(not_done)
        if len(self.futures) == 0:
            self.timer.stop()

        for d in done:
            try:
                value, exception = d.result(), None
            except Exception as e:
                value, exception = None, e
            try:
                if self._aborted:
                    value, exception = None, BackgrounderAbort("aborted jobs")
                if d._status_callbacks != None and hasattr(
                    d._status_callbacks, "terminated"
                ):
                    d._status_callbacks.terminated(exception)
                if (
                    exception == None
                    and d._status_callbacks != None
                    and hasattr(d._status_callbacks, "complete")
                ):
                    d._status_callbacks.complete()
                if exception == None:
                    d._gen.send(value)
                else:
                    d._gen.throw(exception)
            except StopIteration:
                pass
            except:
                # Log errors as unhandled if not caught in the async load generator.
                sys.excepthook(*sys.exc_info())

        for d in not_done:
            if d._status_callbacks != None and hasattr(
                d._status_callbacks, "continuing"
            ):
                d._status_callbacks.continuing()
