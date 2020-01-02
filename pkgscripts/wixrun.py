import os
import re
import subprocess
import mako.template as template
import rtxsite

BASE_DIR = os.path.dirname(os.path.dirname(os.path.normpath(__file__)))
PACK_DIR = os.path.join(BASE_DIR, 'pkgscripts')
PACKB_DIR = os.path.join(BASE_DIR, 'build')
SRC_DIR = os.path.join(BASE_DIR, 'build', 'installer')

if not os.path.exists(PACKB_DIR):
    os.mkdir(PACKB_DIR)
os.chdir(PACK_DIR)

class LMS:
    VERSION = rtxsite.__version__
    ORGNAME = 'Mohler'

WIX_BIN = r'C:\Program Files (x86)\WiX Toolset v3.11\bin'
CANDLE = os.path.join(WIX_BIN, 'candle.exe')
LIGHT = os.path.join(WIX_BIN, 'light.exe')
SHORT_COUNT = 0

def shortened_to_72(identifier):
    global SHORT_COUNT
    if len(identifier) > 72:
        SHORT_COUNT += 1
        identifier = identifier[:32] + 'SHRT{:04n}'.format(SHORT_COUNT) + identifier[-32:]
    return identifier

def tempname(name):
    return os.path.join(PACKB_DIR, name)

class Component:
    def __init__(self, dirname, fname):
        self._dirname = dirname
        self.fname = fname

    @property
    def compid(self):
        if not hasattr(self, '_compid'):
            self._compid = shortened_to_72('comp_'+re.sub(r'[\\.-]', '_', self.source))
        return self._compid

    @property
    def fileid(self):
        if not hasattr(self, '_fileid'):
            self._fileid = shortened_to_72('file_'+re.sub(r'[\\.-]', '_', self.source))
        return self._fileid

    @property
    def dirname(self):
        return self._dirname[len(SRC_DIR)+1:]

    @property
    def source(self):
        return os.path.join(self.dirname, self.fname)

COMPS = None
def _components():
    for dirname, subdirs, fnames in os.walk(os.path.join(SRC_DIR, 'binary')):
        for fname in fnames:
            yield Component(dirname, fname)

def components(basedir=None):
    global COMPS
    if COMPS == None:
        COMPS = list(_components())
    if basedir != None:
        return [c for c in COMPS if c.dirname.startswith(basedir)]
    else:
        return COMPS

def wxs_render():
    outfn = tempname('lmssuite-{}.wxs'.format(LMS.VERSION))
    r1 = open('lmssuite.wxs', 'r').read()
    r2 = template.Template(r1).render(LMS=LMS, components=components)
    open(outfn, 'w').write(r2)
    return outfn

def run_wix():
    fwxs = wxs_render()
    wixobj = tempname('lmssuite.wixobj')
    msiname = os.path.join(BASE_DIR, 'build', 'lmsSuite-{0.ORGNAME}-{0.VERSION}.msi'.format(LMS))

    subprocess.call([CANDLE, '-nologo', fwxs, '-arch', 'x64', '-o', wixobj])
    subprocess.call([LIGHT, '-nologo', wixobj, '-sw1076', '-o', msiname, '-b', SRC_DIR])
