"""
rtlib (as named from LIBrary of Rich Types) is collection of functions and
classes for sending structured data from a server component to a client
component along with rich semantic information about what the data is.  The
central object is a table with column meta-data including labels, output
formatters, and descriptive type strings to be decoded and used in building a
UI.
"""

from .boa import *
from .formatters import *
from .reportcore import *
from .html import *
from .client import *
from .basic_types import *
