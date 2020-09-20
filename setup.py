#!/usr/bin/env python

import os
import re
from distutils.core import setup

root = os.path.dirname(os.path.normpath(__file__))
with open(os.path.join(root, "rtxsite", "__init__.py"), "r") as fd:
    contents = fd.read()
    ver = re.search(r"^__version__ *= *['\"](.*)['\"]$", contents, re.MULTILINE).group(
        1
    )

setup(
    name="rtxsite",
    version=ver,
    description="WPSG site configuration",
    author="Joel B. Mohler",
    author_email="jmohler@thefirestore.com",
    packages=["rtxsite"],
)
