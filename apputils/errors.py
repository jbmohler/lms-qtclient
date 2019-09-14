import sys
import traceback
import tempfile
from QtShim import QtCore, QtWidgets
from . import xplatform

def guiexcepthook(type_, value, tb):
    """
    Replace sys.excepthook with this function to display errors more gracefully 
    for an application which is not associated with a console.
    
    >>> import sys
    >>> import apputils
    >>> sys.excepthook = apputils.guiexcepthook
    """
    try:
        f = open(tempfile.mktemp(prefix='qtalchemy-error-', suffix='.txt'), "w")
        traceback.print_exception(type_, value, tb, limit=None, file=f)

        xplatform.xdg_open(f.name)
    except:
        traceback.print_exception(type_, value, tb, limit=None, file=sys.stderr)

def frame_tuples(stack):
    # Flatten stack frames to list of tuples
    if sys.version_info[:2] <= (3, 5):
        return [tuple(fs) for fs in reversed(stack)]
    else:
        return [(fs.filename, fs.lineno, fs.name, fs.line) for fs in reversed(stack)]

class ExceptionLogger(QtCore.QObject):
    """
    Replace sys.excepthook with this function to display errors more gracefully
    for an application which is not associated with a console.
    
    >>> import sys
    >>> sys.excepthook = ExceptionLogger().excepthook
    """
    # A major reason to make this class a QObject is to take advantage of the
    # thread safety given by the signal/slot mechanism.
    error_event = QtCore.Signal(str, object)

    def __init__(self, parent):
        super(ExceptionLogger, self).__init__(parent)
        self._logname = tempfile.mktemp(prefix='log-error-', suffix='.txt')
        self._log = open(self._logname, 'w')

    def excepthook(self, exc_type, exc_value, exc_traceback):
        try:
            details = { \
                    'exc_type': exc_type.__name__,
                    'exception': str(exc_value),
                    'frames': frame_tuples(traceback.extract_tb(exc_traceback, 5))}
            des = str(exc_value)
            self.error_event.emit(des, details)

            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=self._log)
            self._log.flush()
        except:
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=None, file=sys.stderr)
            des = str(exc_value)
            self.error_event.emit(des, None)

    def show(self):
        xplatform.xdg_open(self._logname)

def exception_message(parent, message):
    # TODO:  Constructing error messages for the user seems to be an
    # application level item.  Accordingly this message cannot be effectively
    # coded at this level.
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setWindowTitle(QtWidgets.QApplication.applicationName())
    msgBox.setIcon(QtWidgets.QMessageBox.Critical)

    type_, value, tb = sys.exc_info()
    msgBox.setText('{}\n\nException message:  {}'.format(message, str(value)))
    msgBox.setDetailedText('\n'.join(traceback.format_exception(type_, value, tb)))

    msgBox.exec_()
