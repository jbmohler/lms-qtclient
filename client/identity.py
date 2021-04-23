import os.path
import cliutils


IDENTITY = {}


def update_identity(**kwargs):
    global IDENTITY
    IDENTITY.update(kwargs)


def get_identity_key(keyname):
    global IDENTITY
    return IDENTITY.get(keyname)


def get_appdata_dir():
    base = cliutils.local_appdata_path()
    return os.path.join(base, get_identity_key("app_slug"))
