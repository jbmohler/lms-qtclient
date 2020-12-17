from PySide6 import QtGui


class UpperValidator(QtGui.QValidator):
    def validate(self, input_str, pos):
        # strip & upper
        cleaned = "".join([a for a in input_str if 32 <= ord(a) < 128])
        return QtGui.QValidator.Acceptable, cleaned.upper(), pos


class BlankableIntValidator(QtGui.QIntValidator):
    def validate(self, input_str, pos):
        if input_str == "":
            return QtGui.QValidator.Acceptable, input_str, pos
        else:
            return super(BlankableIntValidator, self).validate(input_str, pos)


class BlankableFloatValidator(QtGui.QDoubleValidator):
    def validate(self, input_str, pos):
        if input_str == "":
            return QtGui.QValidator.Acceptable, input_str, pos
        else:
            return super(BlankableFloatValidator, self).validate(input_str, pos)
