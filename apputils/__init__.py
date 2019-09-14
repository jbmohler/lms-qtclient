from .geometry import *
from .models import *
from .viewmenus import *
from .errors import *
from .messages import *
from .modwidgets import *
from .globwidgets import *
from .backgrounder import *
from .xplatform import *

def transient_app():
    app = QtWidgets.QApplication.instance()
    if app == None:
        app = QtWidgets.QApplication([])
    return app
