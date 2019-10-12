"""
The mixin here describes a generic value getter & setter for widgets so that
any rtlib based data type can be handled with-out precise knowledge of the
exact widget used.
"""
from PySide2 import QtCore

class ModValueError(ValueError):
    pass

class ModifiedMixin:
    # Widgets implementing ModifiedMixin are expected to have methods `value`
    # and `setValue` as well as the methods given here.   Their change
    # notification signals should be routed through the methods implemented
    # here.

    # _modified = 0 (no changes); 2 (changed, not yet set model); 1 (changed and applied)
    def widgetModified(self):
        return self._modified if hasattr(self, '_modified') else 0

    def setWidgetModified(self, mod):
        # this signal is set up in as_modifiable
        if mod:
            self.valueChanged.emit()
            self._modified = 2
        else:
            self._modified = 0

    def setValueApplied(self):
        if self.widgetModified() == 0:
            self.applyValue.emit()
            return
        if self.widgetModified() == 2:
            self.applyValue.emit()
        self._modified = 1

    def set_invalid_feedback(self, invalid=True):
        if invalid:
            self.setStyleSheet(self.INVALID)
        else:
            self.setStyleSheet(self.VALID)
        self.style().unpolish(self)
        self.style().polish(self)

    def clear_invalid(self):
        self.set_invalid_feedback(False)

    def value_or_invalid(self):
        try:
            v = self.value()
        except ModValueError:
            self.set_invalid_feedback(True)
            v = None
        return v

    def test_invalid(self):
        try:
            self.value()
        except:
            self.set_invalid_feedback(True)


def as_modifiable(kls):
    signals = {\
            'valueChanged': QtCore.Signal(),
            'applyValue': QtCore.Signal()}
    return type('Modifiable'+kls.__name__, (kls, ModifiedMixin), signals)

def is_modifiable(e):
    # This is an approximate check for the interface defined by ModifiedMixin.
    # We might want to consider using Python's abc module.
    return hasattr(e, 'setValueApplied')
