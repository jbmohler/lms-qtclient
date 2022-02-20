import sys
import importlib
from PySide6 import QtCore, QtWidgets


def module_ver(name):
    try:
        if name == "Python":
            v = sys.version.split(" ")[0]
        elif name == "PyQt5":
            x = importlib.import_module("PyQt5.QtCore")
            v = x.PYQT_VERSION_STR
        else:
            x = importlib.import_module(name)
            v = x.__version__
    except:
        v = "unknown version"
    return f"{name} ({v})"


def about_box(parent, header):
    modules = [
        "Python",
        QtCore.__name__.split(".")[0],
        "jose",
        "markupsafe",
        "httpx",
        "xlsxwriter",
    ]
    vers = "<br />".join([module_ver(m) for m in modules])
    name = QtWidgets.QApplication.instance().applicationName()
    QtWidgets.QMessageBox.about(
        parent,
        f"About {name}",
        """\
{}<br />
<p>Library Versions:  <br />{vers}</p>""".format(
            header, vers=vers
        ),
    )
