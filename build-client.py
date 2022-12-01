import os
import sys
import subprocess
import PySide6


def save_icons():
    import qtawesome
    from PySide6 import QtCore, QtWidgets

    app = QtWidgets.QApplication()

    pixmap = qtawesome.icon("fa5.copy", color="blue").pixmap(32, 32)
    pixmap.save("contacts/gui/clip-copy.png")


try:
    save_icons()
except ImportError as e:
    print(str(e))
    if str(e).find("No module named") >= 0 and str(e).find("qtawesome") >= 0:
        print(
            "Skipping icon generation from fontawesome; install qtawesome if desired."
        )
    else:
        raise


def get_qrc_compiler():
    base_name = "pyside6-rcc"
    if sys.platform.lower().startswith("win"):
        base_name += ".exe"
    qrc_compiler = os.path.join(PySide6.__path__[0], base_name)
    if not os.path.exists(qrc_compiler):
        qrc_compiler = base_name
    return qrc_compiler


RCC = get_qrc_compiler()

ROOTED = [
    ("lmssystem/lmsicons.qrc", "lmsicons.py"),
    ("apputils/rtxassets.qrc", "rtxassets.py"),
    ("apputils/widgets/icons.qrc", "icons.py"),
    ("contacts/gui/icons.qrc", "icons.py"),
    ("client/qt/icons.qrc", "icons.py"),
]

ROOTTUPLE = [p[0].rsplit("/", 1) + [p[1]] for p in ROOTED]

for R in ROOTTUPLE:
    path = R[0].replace("/", os.path.sep)
    qrc_file = os.path.join(path, R[1])
    py_file = os.path.join(path, R[2])
    print(R)
    # print([RCC, qrc_file, "-o", py_file])
    subprocess.run([RCC, qrc_file, "-o", py_file])
    # os.system(r'{RCC} {PATH}\{IN} -py3 -o {PATH}\{OUT}'.format(RCC=RCC, PATH=R[0], IN=R[1], OUT=R[2]))
