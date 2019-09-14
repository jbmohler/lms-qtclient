import os
import winreg
import ctypes

def local_appdata_path():
    """
    Windows specific function to get the local appdata directory.
    """
    from ctypes import wintypes, windll
    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [\
                                wintypes.HWND,
                                ctypes.c_int,
                                wintypes.HANDLE,
                                wintypes.DWORD, wintypes.LPCWSTR]


    CSIDL_LOCAL_APPDATA = 28
    path_buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    _ = _SHGetFolderPath(0, CSIDL_LOCAL_APPDATA, 0, 0, path_buf)
    result = path_buf.value
    if result in ['', None]:
        raise RuntimeError('error gettings shell folder path CSIDL_LOCAL_APPDATA')
    return result

def info_message(msg):
    MessageBox = ctypes.windll.user32.MessageBoxW
    MessageBox(None, msg, 'RTX Fido Tool', 0)

def get_vitals():
    return None, None, None
    return os.environ['RTX_SOURCE_ROOT'], os.environ['RTX_CONFIG_FILE'], None

    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    try:
        key = winreg.OpenKey(reg, r"SOFTWARE\RTX")
    except FileNotFoundError as e:
        return None, None, None
    try:
        sr_value, _ = winreg.QueryValueEx(key, 'SourceRoot')
    except FileNotFoundError as e:
        sr_value = None
    try:
        cf_value, _ = winreg.QueryValueEx(key, 'ConfigFile')
    except FileNotFoundError as e:
        cf_value = None
    try:
        server_value, _ = winreg.QueryValueEx(key, 'Server')
    except FileNotFoundError as e:
        server_value = None
    key.Close()
    return sr_value, cf_value, server_value
