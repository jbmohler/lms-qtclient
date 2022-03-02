import io
import json
import datetime
import decimal


class MatrixLink:
    @classmethod
    def loaded(cls, v):
        v = v or []

        self = cls()
        self.original = set(v)
        self.add = set()
        self.remove = set()
        return self

    def serialized(self):
        return {"add": list(self.add), "remove": list(self.remove)}

    def linked(self, other):
        return other in ((self.original - self.remove) | self.add)

    def toggle_linked(self, other, toggled):
        if toggled:
            self.remove.discard(other)
            if other not in self.original:
                self.add.add(other)
        else:
            self.add.discard(other)
            if other in self.original:
                self.remove.add(other)


# other places as well, but this is canonical and the others should be swallowed


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, datetime.time):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, MatrixLink):
            return o.serialized()

        return json.JSONEncoder.default(self, o)


def serialize(thing, pprint=False):
    if pprint:
        return json.dumps(thing, cls=DateTimeEncoder, indent=4)
    else:
        return json.dumps(thing, cls=DateTimeEncoder)


def to_json(thing):
    return io.BytesIO(serialize(thing).encode("utf8"))
