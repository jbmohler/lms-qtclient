"""
This module tracks two things:

    - path of Python modules (aka runtime Mercurial repository)
    - Database credentials & configuration
"""
import os
import sys
import site
import configparser

if sys.platform == 'win32':
    from .winsite import *
else:
    from .unixsite import *

source, config_file, server = get_vitals()

if not getattr(sys, 'rtx_packaged_app', False) or not getattr(sys, 'frozen', False):
    if source != None:
        site.addsitedir(source)

def add_fidolib_site(zipname, timeout=None):
    global server
    import requests

    p = local_appdata_path()
    dirname = os.path.join(p, 'RTXinc', 'Fido Suite', 'Client')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    zipfile = os.path.join(dirname, zipname)

    questions = 'If you have any questions contact Ken or Joel.'

    kwargs = {}
    if timeout != None:
        kwargs['timeout'] = timeout
    r = None
    try:
        r = requests.get(server+'/install/'+zipname, **kwargs)
    except requests.exceptions.Timeout as e:
        if not os.path.exists(zipfile):
            info_message('The server {} could not be contacted.  This program must be connected to the RTX network.  {}'.format(server, questions))
            sys.exit(1)
    if r == None or r.status_code != 200:
        if not os.path.exists(zipfile):
            info_message('The file {} could not be downloaded.  {}'.format(server+'/install/'+zipname, questions))
            sys.exit(1)
    else:
        with open(zipfile, 'wb') as fd:
            for chunk in r.iter_content(1024*16):
                fd.write(chunk)

    sys.path.append(zipfile)

class ConfigKeyProxy:
    def __init__(self, proxy, section):
        self.proxy = proxy
        self.section = section

    def __getattr__(self, name):
        try:
            return self.proxy.parser.get(self.section, name)
        except configparser.NoSectionError:
            return None
        except configparser.NoOptionError:
            return None

class ConfigProxy:
    def __init__(self, source_file):
        self.parser = configparser.ConfigParser()
        if source_file != None:
            self.parser.read(source_file)

    def __getitem__(self, section):
        return ConfigKeyProxy(self, section)

config = ConfigProxy(config_file)

__version__ = '0.5.1.0'
