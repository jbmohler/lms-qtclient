from .geometry import * # noqa: F401
from .models import * # noqa: F401
from .viewmenus import * # noqa: F401
from .errors import * # noqa: F401
from .messages import * # noqa: F401
from .modwidgets import * # noqa: F401
from .globwidgets import * # noqa: F401
from .backgrounder import * # noqa: F401
from PySide2 import QtWidgets

def transient_app():
    app = QtWidgets.QApplication.instance()
    if app == None:
        app = QtWidgets.QApplication([])
    return app
