
class Controller:
    def preset_group(self, **kwargs):
        pass

    def values_preset(self):
        pass

    def values_changed(self):
        pass

class ControlledModelRow:
    controller = None

    def __setattr__(self, attr, value):
        super(ControlledModelRow, self).__setattr__(attr, value)
        if self.controller != None and not self._multiset_:
            self.value_changed(self, attr)
