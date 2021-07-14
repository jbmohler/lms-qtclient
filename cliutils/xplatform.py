##############################################################################
#       Copyright (C) 2010-2021, Joel B. Mohler <joel@kiwistrawberry.us>
#
#  Distributed under the terms of the GNU Lesser General Public License (LGPL)
#                  http://www.gnu.org/licenses/
##############################################################################
"""
These functions recognize Windows, Linux and WSL.   They perform the
appropriate logic for each.
"""

import os
import sys
import platform


def is_wsl():
    return "microsoft" in platform.uname()[3].lower()


def is_windows():
    """
    returns True if running on windows
    """
    return sys.platform in ("win32", "cygwin")


def is_mac():
    """
    returns True if running on Mac
    """
    return platform.system() == "Darwin"


def xdg_open(viewfile):
    """
    Be a platform smart incarnation of xdg-open and open files in the correct
    application.
    """

    escaped = viewfile.replace(";", r"\;").replace("&", r"\&")

    if is_windows():
        from ctypes import windll

        windll.shell32.ShellExecuteW(0, "open", viewfile, None, None, 1)
    elif is_wsl():
        os.system(f'powershell.exe /c start "{escaped}"')
    elif is_mac():
        os.system(f'open "{escaped}"')
    else:
        os.system(f'xdg-open "{escaped}"')


def local_appdata_path_win32():
    """
    Windows specific function to get the local appdata directory.
    """
    import ctypes
    from ctypes import wintypes, windll

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPCWSTR,
    ]

    CSIDL_LOCAL_APPDATA = 28
    path_buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    _ = _SHGetFolderPath(0, CSIDL_LOCAL_APPDATA, 0, 0, path_buf)
    return path_buf.value


def local_appdata_path_unix():
    return os.path.join(os.environ["HOME"], ".config")


local_appdata_path = (
    local_appdata_path_win32 if is_windows() else local_appdata_path_unix
)
