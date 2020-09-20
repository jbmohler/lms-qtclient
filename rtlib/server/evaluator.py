import io
import ast
import tokenize


class PreparedEvaluator:
    """
    The evaluate method of this object take plain old Python object like `t` in
    the following snippet.

    >>> class X: pass
    >>> t = X()
    >>> t.name = 'Fred Smith'
    >>> t.age = 23

    The members of the class form the evaluation globals for the Python code
    expression passed to __init__.  The preparation phase inspects the
    expression for the required attributes from the object.  This liberates us
    from having to declare all the attributes and optimizes the evaluation by
    ensuring that we don't access unnecessary attributes with expensive
    getters.

    Very simple evaluations are simple.

    >>> p = PreparedEvaluator('age')
    >>> p.evaluate(t)
    23

    The members retain their full Python identity.

    >>> p = PreparedEvaluator('name.split(" ")[1]')
    >>> p.evaluate(t)
    'Smith'

    In addition to parsing the expression for names, it also transforms '=' to
    '==' for convenience.  This is unambiguous since this is designed for
    single line evaluations (similar to lambda) and assignments are not
    allowed.

    >>> p = PreparedEvaluator('age=23')
    >>> p.evaluate(t)
    True

    Here are some more tests:

    >>> PreparedEvaluator('age=20 or age=26').evaluate(t)
    False
    >>> PreparedEvaluator('age=20 or name[0]="F"').evaluate(t)
    True
    >>> PreparedEvaluator('30 < age < 32').evaluate(t)
    False
    >>> PreparedEvaluator('20 < age < 40').evaluate(t)
    True
    """

    def __init__(self, expr):
        rl = io.StringIO(expr).readline
        assignments = [
            t[2]
            for t in tokenize.generate_tokens(rl)
            if t.type == tokenize.OP and t.string == "="
        ]
        for a in reversed(assignments):
            if a[0] != 1:
                raise ValueError("the expression must be one line")
            expr = expr[: a[1]] + "==" + expr[a[1] + 1 :]

        self._code = compile(expr, "<string>", "eval")

        self._names = []
        t = ast.parse(expr)
        for n in ast.walk(t):
            if n.__class__.__name__ == "Name":
                self._names.append(n.id)

    def evaluate(self, obj):
        evaldict = {n: getattr(obj, n) for n in self._names}
        return eval(self._code, evaldict)
