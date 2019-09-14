import valix
import contextlib
import rtlib

class FieldList(set):
    def intersects(self, iter):
        for w in iter:
            if w in self:
                return True
        return False

class ModelRow:
    controller = None

    def __setattr__(self, attr, value):
        super(ModelRow, self).__setattr__(attr, value)
        if self.controller != None and \
                not getattr(self, '_init_block', False) and \
                not getattr(self, '_multiset', False) and \
                attr not in ('_init_block', '_multiset', '_recurse'):
            print(value)
            self.controller.fields_changed(self, FieldList([attr]))

    def multiset(self, **kwargs):
        try:
            self._multiset = True
            self.controller.preset_group(self, kwargs)
            for key, value in kwargs.items():
                setattr(self, key, value)
        finally:
            self._multiset = False
        self.controller.fields_changed(self, FieldList(kwargs.keys()))

class Lockout:
    def __init__(self, row, label):
        self.row = row
        self.label = label
        self.first = None

    def __enter__(self):
        if not hasattr(self.row, '_recurse'):
            self.row._recurse = {}

        self.first = self.row._recurse.get(self.label, 0) == 0
        if self.label in self.row._recurse:
            self.row._recurse[self.label] += 1
        else:
            self.row._recurse[self.label] = 1
        return self

    def __exit__(self, *args):
        self.row._recurse[self.label] -= 1

def recurse_locked(row, label):
    if not hasattr(row, '_recurse'):
        row._recurse = {}
    return row._recurse.get(label, 0) > 0

def recurse_lockout(row, label):
    return Lockout(row, label)

class Logger:
    def __init__(self):
        self.logs = []

    @property
    def count(self):
        return len(self.logs)

    def dblog(self, resource):
        self.logs.append(resource)

class MultiController:
    def __init__(self, *args):
        self.controllers = list(args)

    def preset_group(self, *args):
        for cntlr in self.controllers:
            if hasattr(cntlr, 'preset_group'):
                cntlr.preset_group(*args)

    def fields_changed(self, *args):
        for cntlr in self.controllers:
            cntlr.fields_changed(*args)

    @property
    def session(self):
        return self.controllers[0].session


class Controller:
    @contextlib.contextmanager
    def database_hit_logger(self):
        if not hasattr(self, '_logger_list'):
            self._logger_list = []

        dest = Logger()
        self._logger_list.append(dest)
        try:
            yield dest
        finally:
            self._logger_list.remove(dest)

    def dblog(self, resource):
        if hasattr(self, '_logger_list'):
            for l in self._logger_list:
                l.dblog(resource)


