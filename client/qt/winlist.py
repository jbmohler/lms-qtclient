from PySide2 import QtCore


def init(main_winid):
    app = QtCore.QCoreApplication.instance()
    app._windows = []
    app._main_winid = main_winid


def register(w, title):
    app = QtCore.QCoreApplication.instance()
    app._windows.append((w, title))


def unregister(w):
    app = QtCore.QCoreApplication.instance()
    for index, ww in enumerate(app._windows):
        if ww[0] is w:
            del app._windows[index]
            break


def main_window():
    app = QtCore.QCoreApplication.instance()
    for w in app._windows:
        if app._main_winid == w[1]:
            return w[0]
    return app._windows[0][0]


def close_all():
    app = QtCore.QCoreApplication.instance()
    for w in app._windows[:]:  # NOTE:  must grab a copy of the list
        w[0].close()
