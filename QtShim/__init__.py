import sys
if sys.version_info[:2] == (3, 4):
    from PySide import QtCore, QtGui as QtWidgets, QtGui, QtWebKit as QtWebEngineWidgets

    class ShimWebView(QtWebEngineWidgets.QWebView):
        pass

    QtCore.QSortFilterProxyModel = QtGui.QSortFilterProxyModel

    def local_init_application():
        settings = QtWebEngineWidgets.QWebSettings.globalSettings()
        settings.setFontFamily(QtWebEngineWidgets.QWebSettings.StandardFont, 'Tahoma')
        settings.setFontSize(QtWebEngineWidgets.QWebSettings.DefaultFontSize, 11)

    QtWidgets.local_init_application = local_init_application

use_pyside = True

if sys.version_info[:2] >= (3, 5) and use_pyside:
    # Python 3.6 is a proxy check for using Qt 5.11 or greater
    from PySide2 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets, QtWebChannel

    class ShimWebView(QtWebEngineWidgets.QWebEngineView):
        pass

    def local_init_application():
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES)

        settings = QtWebEngineWidgets.QWebEngineSettings.globalSettings()
        settings.setFontFamily(QtWebEngineWidgets.QWebEngineSettings.StandardFont, 'Tahoma')
        settings.setFontSize(QtWebEngineWidgets.QWebEngineSettings.DefaultFontSize, 11)

    QtWidgets.local_init_application = local_init_application

if sys.version_info[:2] >= (3, 5) and not use_pyside:
    # Python 3.6 is a proxy check for using Qt 5.11 or greater
    from PyQt5 import QtCore, QtWidgets, QtGui#`, QtWebEngineWidgets, QtWebChannel
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Property = QtCore.pyqtProperty

    #class ShimWebView(QtWebEngineWidgets.QWebEngineView):
    #    pass

    def local_init_application():
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseOpenGLES)

    #    settings = QtWebEngineWidgets.QWebEngineSettings.globalSettings()
    #    settings.setFontFamily(QtWebEngineWidgets.QWebEngineSettings.StandardFont, 'Tahoma')
    #    settings.setFontSize(QtWebEngineWidgets.QWebEngineSettings.DefaultFontSize, 11)

    QtWidgets.local_init_application = local_init_application
