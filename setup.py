#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="pysharpinventor",
    packages=["pysharpinventor", "pysharpinventor.contrib"],
    version="0.1.0",
    description="Autodesk Inventor Automation for Python",
    author="Nandhakumar",
    author_email="nandhakumar_maint@hotmail.com",
    url="https://github.com/Nandhakumarpro/pysharpinventor",
    install_requires=[
        'pythonnet>=3.0.0',
    ],
    keywords=["inventor", "automation", "clr", "autodesk"],
    license="BSD License",
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
    ],
)
