"""
The KeyEdit provides data sensitive editting for foreign key edits::

- search button
- context menus - for what? (look up referenced entity)
"""

from QtShim import QtGui
from .button_edit import ButtonEdit
from . import icons # noqa: F401

class KeyEdit(ButtonEdit):
    """
    KeyEdit is a QLineEdit derivative that offers a button on the right to 
    search for rows from a database table.  KeyEdit is best used in the 
    InputYoke infrastructure with a DomainEntity derived class.
    """
    def __init__(self, parent=None):
        super(KeyEdit, self).__init__(parent)
        self.button.setIcon(QtGui.QIcon(':/apputils/widgets/edit-find-6.ico'))
