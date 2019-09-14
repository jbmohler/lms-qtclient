
class ValidationError(Exception):
    pass

def constraint(*flds):
    def f2(f):
        if not f.__name__.startswith('require_'):
            raise ValueError('valix constraint functions must start with an approved prefix')
        f.valix_attributes = flds
        return f
    return f2

def class_constraints(cls):
    results = []
    for a in dir(cls):
        if hasattr(getattr(cls, a), 'valix_attributes'):
            results.append(getattr(cls, a))
    return results

def class_validate_rowset(cls, rows):
    funcs = class_constraints(cls)

    invalids = []
    for func in funcs:
        for row in rows:
            try:
                func(row)
            except ValidationError as e:
                for attr in func.valix_attributes:
                    invalids.append((row, attr, str(e)))

    return invalids

def validate_cellset(constraints, cells):
    valids_pre = []
    invalids = []
    for func in constraints:
        for row, attr in cells:
            if attr in func.valix_attributes:
                try:
                    func(row)
                    valids_pre.append((row, attr))
                except ValidationError as e:
                    for attr in func.valix_attributes:
                        invalids.append((row, attr, str(e)))

    valids = [v for v in valids_pre if v not in invalids]
    return valids, invalids
