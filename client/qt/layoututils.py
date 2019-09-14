from QtShim import QtWidgets

def hline():
    toto = QtWidgets.QFrame()
    toto.setFrameShape(QtWidgets.QFrame.HLine)
    toto.setFrameShadow(QtWidgets.QFrame.Sunken)
    return toto

def stretcher():
    empty = QtWidgets.QWidget()
    empty.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    return empty

def horizontal(*widgets):
    w = QtWidgets.QWidget()
    w.layout = QtWidgets.QHBoxLayout(w)
    w.layout.setContentsMargins(0, 0, 0, 0)
    for w2 in widgets:
        w.layout.addWidget(w2)
    w.layout.addStretch(4)
    return w

# Roughly speaking the following two are equivalent:
# 1)  form_widget('&Field', field_edit)
# 2)  horizontal(buddied('&Field', field_edit), field_edit)
def form_widget(label, w):
    w2 = QtWidgets.QWidget()
    f = QtWidgets.QFormLayout(w2)
    f.setContentsMargins(0, 0, 0, 0)
    f.addRow(label, w)
    return w2

def buddied(text, w2):
    w1 = QtWidgets.QLabel(text)
    w1.setBuddy(w2)
    return w1
