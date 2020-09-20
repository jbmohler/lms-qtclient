# -*- coding: utf-8 -*-
##############################################################################
#       Copyright (C) 2010, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################

from PySide2 import QtCore, QtWidgets

# patterned after http://labs.qt.nokia.com/2007/06/06/lineedit-with-a-clear-button/


class ButtonEdit(QtWidgets.QLineEdit):
    buttonPressed = QtCore.Signal(name="buttonPressed")

    def __init__(self, parent=None):
        super(ButtonEdit, self).__init__(parent)
        self.button = QtWidgets.QToolButton(self)
        self.button.setCursor(QtCore.Qt.ArrowCursor)
        self.button.setFocusPolicy(QtCore.Qt.NoFocus)
        # It would seem nice if I could defer this sizing issue to the
        # style-sheet rather than calculating in the resizeEvent.
        # buttonWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        # self.setStyleSheet("QLineEdit {{ padding-right: {0}px; }}".format(buttonWidth))

        self.button.clicked.connect(self.buttonPress)

    def resizeEvent(self, event):
        rect = self.rect()
        frameWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        buttonWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        self.button.resize(buttonWidth, rect.height() - 2 * frameWidth)
        self.button.move(rect.right() - buttonWidth, frameWidth)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F4:
            self.buttonPress()
        else:
            super(ButtonEdit, self).keyPressEvent(event)

    def buttonPress(self):
        self.buttonPressed.emit()
