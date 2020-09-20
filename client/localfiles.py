import os
import platform
import re
import itertools
import tempfile
import datetime


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


if platform.system() == "Windows":
    local_appdata_path = local_appdata_path_win32
else:
    local_appdata_path = local_appdata_path_unix


class LocalDirectory:
    def __init__(self, dirname=None, appname=None, tail=None):
        if appname == None:
            appname = "Mohler"
        if dirname == None:
            p = local_appdata_path()
            if p not in ["", None]:
                dirname = os.path.join(p, appname)
                if tail != None:
                    dirname = os.path.join(dirname, tail)
        if dirname == None:
            dirname = tempfile.mkdtemp(prefix="rtx")
        self.dirname = dirname
        if not os.path.exists(self.dirname):
            os.makedirs(self.dirname)

    def show_browser(self):
        import cliutils

        cliutils.xdg_open(self.dirname)

    def _candidates(self, base, extension):
        yield os.path.join(self.dirname, f"{base}.{extension}")
        for i in itertools.count(1):
            yield os.path.join(self.dirname, f"{base}-{i}.{extension}")

    def user_output_filename(self, title, extension):
        fn_title = re.sub("[/\\&:]", "_", title)
        base = f"{fn_title}-{datetime.datetime.now().isoformat().replace(':', '-')}"

        for candidate in self._candidates(base, extension):
            if not os.path.exists(candidate):
                return candidate

    def join(self, tail):
        return os.path.join(self.dirname, tail)
