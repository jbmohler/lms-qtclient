# -*- coding: utf-8 -*-
##############################################################################
#       Copyright (C) 2010, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################
"""
For the most part, we have functions here which do something for windows 
and something else for everything else.
"""

import os
import sys

def is_windows():
    """
    returns True if running on windows
    """
    return sys.platform in ('win32', 'cygwin')

def xdg_open(file):
    """
    Be a platform smart incarnation of xdg-open and open files in the correct 
    application.
    """
    if is_windows():
        try:
            # we try with win32api because that's cleaner (os.system flickers a command prompt)
            import win32api
            win32api.ShellExecute(0, None, file, None, None, 1)
        except ImportError as e:
            xx = os.system('start {0}'.format(file))
            if xx != 0:
                raise RuntimeError('could not launch file')
    else:
        os.system('xdg-open "{0}"'.format(file.replace(';', r'\;').replace('&', r'\&')))
