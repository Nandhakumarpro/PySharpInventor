#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pysharpinventor",
    packages=find_packages(include=["pysharpinventor", "pysharpinventor.*"]),
    version="0.2.0",
    description="Autodesk Inventor Automation for Python",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Nandhakumar",
    author_email="nandhakumar_maint@hotmail.com",
    url="https://github.com/Nandhakumarpro/PySharpInventor",
    install_requires=[
        'pythonnet>=3.0.0',
    ],
    keywords=["inventor", "automation", "clr", "autodesk"],
    license="BSD-3-Clause",
    license_files=["LICENSE.txt"],
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
    ],
)
