import os
from PySide6 import QtCore, QtWidgets


def message(parent, text, buttons=None, default=None, details=None, richtext="maybe"):
    QMB = QtWidgets.QMessageBox
    name = QtWidgets.QApplication.applicationName()
    box = QMB(parent)
    box.setWindowTitle(name)
    if richtext == "yes":
        box.setTextFormat(QtCore.Qt.RichText)
    elif richtext == "maybe":
        box.setTextFormat(QtCore.Qt.AutoText)
    box.setText(text)
    if details != None:
        box.setDetailedText(details)
    pbuttons = {}
    if buttons == None:
        pbuttons["Ok"] = box.addButton(QMB.Ok)
        icon = QMB.Information
    else:
        for b in buttons:
            if b in ["Yes", "No", "Cancel", "Ok"]:
                pbuttons[b] = box.addButton(getattr(QMB, b))
            else:
                pbuttons[b] = box.addButton(b, QMB.ActionRole)
            if default != None and default == b:
                box.setDefaultButton(pbuttons[b])
        icon = QMB.Information if len(buttons) < 2 else QMB.Question
    box.setIcon(icon)
    box.exec_()
    for name, button in pbuttons.items():
        if button == box.clickedButton():
            return name
    return None


def information(parent, text, details=None):
    message(parent, text.replace("\n", "<br />"), details=details)


def message_cancel(parent, text):
    QMB = QtWidgets.QMessageBox
    name = QtWidgets.QApplication.applicationName()
    return QMB.question(parent, name, text, buttons=QMB.Ok | QMB.Cancel) == QMB.Cancel


def question(parent, text, buttons=None, default=None):
    if buttons == None:
        buttons = ["Yes", "No"]
    return message(parent, text, buttons, default=default)


def get_save_filename(parent, title, filter, dirname=None):
    if QtCore.__name__.split(".")[0] == "PySide":
        filename, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent, title, filter=filter, dir=dirname
        )
    else:
        filename = QtWidgets.QFileDialog.getSaveFileName(
            parent, title, filter=filter, dir=dirname
        )
    if filename == "":
        return None
    filename = filename.replace("/", os.path.sep)
    return filename


def get_open_filename(parent, title, filter, dirname=None):
    if QtCore.__name__.split(".")[0] == "PySide":
        filename, filter = QtWidgets.QFileDialog.getOpenFileName(
            parent, title, filter=filter, dir=dirname
        )
    else:
        filename = QtWidgets.QFileDialog.getOpenFileName(
            parent, title, filter=filter, dir=dirname
        )
    if filename == "":
        return None
    filename = filename.replace("/", os.path.sep)
    return filename
