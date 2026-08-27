#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Hello World example for PySharpInventor
"""

from pysharpinventor import Inventor

# Connect to active Inventor instance
inv = Inventor()

# Print application info
print(f"Inventor Application: {inv.app.Name}")
print(f"Active Document: {inv.doc.Name}")
