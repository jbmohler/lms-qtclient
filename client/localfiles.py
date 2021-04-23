import os
import re
import itertools
import tempfile
import datetime
import cliutils
from . import identity


class LocalDirectory:
    def __init__(self, dirname=None, appname=None, tail=None):
        if appname == None:
            appname = identity.get_identity_key("app_slug")
        if dirname == None:
            p = cliutils.local_appdata_path()
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
