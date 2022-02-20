import os
import sys
import glob
import shutil
import zipfile
import hashlib
import cx_Freeze as cxf
import httpx
import PySide6

# We need to include this import since we don't install wpsgsrc to Python
# site-packages.
import rtxsite
from . import wixrun

GENERATED_EXE = ["lmssuite.exe"]


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            fullfname = os.path.join(root, file)
            # address silly case collisions
            fullfname = (
                fullfname.replace("ConfigParser", "configparser")
                .replace("Queue", "queue")
                .replace("HRESULT", "hresult")
            )
            ziph.write(fullfname, arcname=fullfname[len(path) + 1 :])


def hash_file(path, sha_out):
    hsha = hashlib.sha1()
    blocksize = 4096
    with open(path, "rb") as f1:
        while True:
            chunk = f1.read(blocksize)
            if chunk == b"":
                break
            hsha.update(chunk)
    hstr = hsha.hexdigest()
    with open(sha_out, "wb") as f2:
        f2.write(hstr.encode("ascii"))
    return hstr


def util_zipdir(path, zipfname):
    zipf = zipfile.ZipFile(zipfname, "w")
    zipdir(path, zipf)
    zipf.close()

    hash_file(zipfname, zipfname.replace(".zip", ".sha1.txt"))


class ExeMetadata:
    version = rtxsite.__version__
    long_description = ""
    description = "lms Application Suite"
    author = "Joel B. Mohler"
    name = "lmsSuite"


def fresh_mkdir(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    os.makedirs(dirname)


def main():
    packagedir = os.path.dirname(os.path.normpath(__file__))
    root = os.path.dirname(packagedir)
    scriptsdir = os.path.join(root, "scripts")
    outroot = os.path.join(root, "build", "frozen")
    outroot2 = os.path.join(root, "build", "installer")

    # delete and recreate output directory.
    fresh_mkdir(outroot)
    if os.path.exists(outroot2):
        shutil.rmtree(outroot2)

    zipincludes = [
        "asyncio",
        "chardet",
        "collections",
        "colorama",
        "concurrent",
        "ctypes",
        "curses",
        "dateutil",
        "distutils",
        "docutils",
        "email",
        "encodings",
        "fuzzyparsers",
        "html",
        "http",
        "idna",
        "importlib",
        "jinja2",
        "json",
        "lib2to3",
        "logging",
        "pkg_resources",
        "pydoc_data",
        "pygments",
        "pytz",
        "httpx",
        "setuptools",
        "urllib",
        "urllib3",
        "wpsgsite",
        "wsgiref",
        "xlsxwriter",
        "xml",
        "xmlrpc",
    ]

    rezipset = [
        "apputils",
        "comtypes",
        "ewtools",
        "valix",
        "rtlib",
        "fidocore",
        "fidolib",
        "purchasing",
        "scanners",
    ]
    other_exclusions = ["PySide6", "certifi", "Crypto", "sqlite3"]

    # Icons are created easily from .png files at http://www.xiconeditor.com/

    lms = cxf.Executable(
        os.path.join(scriptsdir, "guishell.py"),
        targetName=GENERATED_EXE[0],
        base="Win32GUI",
        icon=os.path.join(root, "pkgscripts", "lms_basic.ico"),
    )

    includes = [
        "apputils.widgets.columnchooser",
        "apputils.widgets.icons",
        "client.qt.reportdock",
        "client.qt.reports",
        "client.qt.serverdlgs",
        "client.qt.winlist",
        "contacts.gui",
        "pyhacc.gui",
        "rtlib.server.evaluator",
    ]

    freezer = cxf.Freezer(
        [lms],
        includes=includes,
        includeFiles=[],
        excludes=["tkinter", "pyreadline", "IPython", "tornado", "sitesql", "psycopg2"],
        # excludes=['numpy', 'pyreadline'],
        targetDir=os.path.join(outroot, "binary"),
        zipIncludePackages=zipincludes,
        zipExcludePackages=rezipset + other_exclusions,
        metadata=ExeMetadata,
    )

    freezer.Freeze()

    shutil.copyfile(
        os.path.join(root, "pkgscripts", "lms_basic.ico"),
        os.path.join(outroot, "binary", "lms_basic.ico"),
    )
    shutil.copyfile(
        os.path.join(root, "pkgscripts", "assets", "lms_basic.png"),
        os.path.join(outroot, "binary", "lms_basic.png"),
    )

    # scrubbing PySide6
    PySideDeletes = [
        "examples",
        "glue",
        "include",
        "qml",
        "scripts",
        "support",
        "translations",
    ]
    print("delete PySide6 subdirectories")
    for psd in PySideDeletes:
        x = os.path.join(outroot, "binary", "lib", "PySide6", psd)
        print(x)
        shutil.rmtree(x)
    web2 = glob.glob(os.path.join(outroot, "binary", "lib", "PySide6", "*WebEngine*.*"))
    web2 += glob.glob(
        os.path.join(outroot, "binary", "lib", "PySide6", "*WebChannel*.*")
    )
    print("delete PySide6 Web elements:")
    for x in web2:
        print(x)
        os.unlink(x)

    shutil.copyfile(httpx.certs.where(), os.path.join(outroot, "binary", "cacert.pem"))
    shutil.copytree(
        os.path.join(PySide6.__path__[0], "openssl"),
        os.path.join(outroot, "binary", "lib", "openssl"),
    )
    shutil.copyfile(
        os.path.join(root, "pkgscripts", "redist", "vcruntime140.dll"),
        os.path.join(outroot, "binary", "vcruntime140.dll"),
    )
    for mexe in GENERATED_EXE:
        shutil.copyfile(
            os.path.join(root, "pkgscripts", "app.config"),
            os.path.join(outroot, "binary", f"{mexe}.config"),
        )

    # os.startfile(os.path.join(outroot, 'binary'))
    # os.startfile(os.path.join(outroot, 'binary', 'lmssuite.exe'))

    print(outroot, outroot2)
    shutil.copytree(outroot, outroot2)

    # refiddle library.zip
    # z2 = zipfile.ZipFile(os.path.join(outroot2, 'binary', 'library.zip'), 'r')
    # items = z2.namelist()
    # items.sort(key=lambda x: x.lower())
    # for i in range(len(items)-1):
    #    if items[i].lower() == items[i+1].lower():
    #        if items[i].split('.')[0] not in ['ConfigParser', 'Queue', 'importlib/__init__']:
    #            raise RuntimeError('Archive item {} is ambiguously cased and unaccounted for elsewhere'.format((items[i], items[i+1])))
    # z2.extractall(outlibzip)

    """
    outlibzip = os.path.join(outroot2, 'binary', 'lib')
    fresh_mkdir(outfidomainzip)
    #FZIP = ['apputils', 'comtypes', 'ewtools', 'valix', 'rtlib', 'fidocore', 'fidolib', 'purchasing', 'scanners']
    for local in rezipset:
        shutil.copytree(os.path.join(outlibzip, local), os.path.join(outfidomainzip, local))
    fresh_mkdir(outscancountzip)
    #SCZIP = ['apputils', 'comtypes', 'ewtools', 'valix', 'rtlib', 'fidocore', 'fidolib', 'purchasing', 'scanners']
    for local in rezipset:
        shutil.copytree(os.path.join(outlibzip, local), os.path.join(outscancountzip, local))
    fresh_mkdir(outsnsaleszip)
    #RAZIP = ['apputils', 'comtypes', 'ewtools', 'valix', 'rtlib', 'fidocore', 'fidolib', 'purchasing', 'scanners']
    for local in rezipset:
        shutil.copytree(os.path.join(outlibzip, local), os.path.join(outsnsaleszip, local))
    fresh_mkdir(outscantrayzip)
    #STZIP = ['apputils', 'comtypes', 'ewtools', 'valix', 'rtlib', 'fidocore', 'fidolib', 'purchasing', 'scanners']
    for local in rezipset:
        shutil.copytree(os.path.join(outlibzip, local), os.path.join(outscantrayzip, local))
    for local in set(rezipset):
        shutil.rmtree(os.path.join(outlibzip, local))
    #util_zipdir(outlibzip, os.path.join(outroot2, 'binary', 'library.zip'))
    if sys.version_info[:2] >= (3, 6):
        tail = '36.zip'
    else:
        tail = '.zip'
    util_zipdir(outfidomainzip, os.path.join(root, 'build', 'fidomain'+tail))
    util_zipdir(outscancountzip, os.path.join(root, 'build', 'scancount'+tail))
    util_zipdir(outsnsaleszip, os.path.join(root, 'build', 'snsales'+tail))
    util_zipdir(outscantrayzip, os.path.join(root, 'build', 'scantray'+tail))
    #shutil.rmtree(outlibzip)
    shutil.rmtree(outfidomainzip)
    shutil.rmtree(outscancountzip)
    shutil.rmtree(outsnsaleszip)
    shutil.rmtree(outscantrayzip)
"""

    # create msi
    wixrun.run_wix()

    return outroot
