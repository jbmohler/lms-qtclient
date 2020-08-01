# -*- coding: utf-8 -*-
##############################################################################
#       Copyright (C) 2012, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################

qt_bindings = 'PySide'
if qt_bindings == 'PyQt4':
    # we wish to only touch sip if we're PyQt4 based (otherwise sip is unnecessary)
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)

from .dockers import *
from .calendar import CalendarView, CalendarTopNav

__version_info__ = ['0', '4', '0']
__version__ = '.'.join(__version_info__)
