from PySide2 import QtCore
import pytest
# pylint: disable=import-error
import rtxsite # pylint: disable=unused-import
import apputils
import apputils.widgets as widgets

@pytest.mark.gui
def test_chooser():
    app = apputils.transient_app()
    w = widgets.TableView()
    m = apputils.ObjectQtModel([\
            apputils.Column('s1', 'C1'),
            apputils.Column('s2', 'C2'),
            apputils.Column('s3', 'C3'),
            apputils.Column('s4', 'C4'),
            apputils.Column('s5', 'C5'),
            apputils.Column('s6', 'C6')])
    w.setModel(m)
    w.show()
    app.exec_()

if __name__ == '__main__':
    test_chooser()
