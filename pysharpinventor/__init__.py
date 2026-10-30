#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pysharpinventor
    ~~~~~~~~~~~~~~~

    Autodesk Inventor Automation for Python.

    :copyright: (c) 2026
    :license: BSD, see LICENSE.txt for more details.
"""
__docformat__ = 'restructuredtext en'
__version__ = '0.2.0'

from pysharpinventor.api import *
from pysharpinventor import geometry  # registers Edge/Face extension methods
from pysharpinventor import selectors  # registers select_faces/select_edges/select_vertices
