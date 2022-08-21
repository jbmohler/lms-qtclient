import math
import fuzzyparsers


def as_xlsx(xlsx_formatter):
    def dec(f):
        f.as_xlsx = xlsx_formatter
        return f

    return dec


def allow_none(func):
    func.allow_none = True
    return func


def date_formatter(value):
    if value == None:
        return ""
    return value.strftime("%m/%d/%Y")


def datetime_formatter(value):
    if value == None:
        return ""
    return value.strftime("%m/%d/%Y %I:%M %p")


def integer_formatter(value):
    if value == None:
        return "--"
    return f"{int(value):,}"


def filesize_formatter(value):
    if value == None:
        return ""

    return f"{math.ceil(value / 1024):,} KB"


def dollar_formatter(value, blankzero=False):
    """
    >>> dollar_formatter(-0.230001)
    '-0.23'
    >>> dollar_formatter(-12.230001)
    '-12.23'
    >>> dollar_formatter(298357.)
    '298,357.00'
    >>> dollar_formatter(-298357.)
    '-298,357.00'
    """
    if value is None:
        value = 0.0
    # check for close to floating point zero
    if blankzero and abs(value) < 0.001:
        return ""
    return f"{value:,.2f}"


def percent_formatter(value):
    return f"{value:,.1%}"


@allow_none
def fixedpoint_nan_formatter(value, decimals):
    """
    >>> fixedpoint_nan_formatter(3.13, 5)
    '3.13000'
    >>> fixedpoint_nan_formatter(3.136, 2)
    '3.14'
    >>> fixedpoint_nan_formatter(10835.8924, 2)
    '10,835.89'
    """
    if value == None:
        return "--"
    return "{:,.{}f}".format(value, decimals)


# reverse formatting ... roughly coercing strings #
def currency_coerce(value):
    if value in ["", None]:
        return None
    if isinstance(value, str) and "," in value:
        value = value.replace(",", "")
    return float(value)


def float_coerce(value):
    if value in ["", None]:
        return None
    if isinstance(value, str) and "," in value:
        value = value.replace(",", "")
    return float(value)


def date_coerce(value):
    if value == "":
        return None
    return fuzzyparsers.parse_date(value)
