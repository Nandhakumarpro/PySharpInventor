#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pysharpinventor._interop
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lazy loader for the Autodesk Inventor Interop assembly.

    :copyright: (c) 2026
    :license: BSD, see LICENSE.txt for more details.
"""

import os
import glob
import logging

logger = logging.getLogger(__name__)


class InventorConnectionError(Exception):
    """Raised when unable to connect to Inventor"""
    pass


class InventorVersionNotFoundError(Exception):
    """Raised when Inventor installation is not found"""
    pass


_module = None
_dll_path = None


def find_inventor_dll():
    """Find the Inventor Interop DLL, preferring the newest installed version"""
    base_paths = [
        r"C:\Program Files\Autodesk",
        r"C:\Program Files (x86)\Autodesk"
    ]

    for base_path in base_paths:
        if not os.path.exists(base_path):
            continue

        # Reverse sort so "Inventor 2025" is tried before "Inventor 2023"
        inventor_dirs = sorted(glob.glob(os.path.join(base_path, "Inventor *")), reverse=True)
        for inventor_dir in inventor_dirs:
            dll_path = os.path.join(
                inventor_dir,
                "Bin",
                "Public Assemblies",
                "Autodesk.Inventor.Interop.dll"
            )
            if os.path.exists(dll_path):
                logger.info(f"Found Inventor at: {dll_path}")
                return dll_path

    return None


def load_interop(dll_path=None):
    """
    Load the Inventor Interop assembly once and return the ``Inventor`` namespace.

    :param dll_path: Optional path to Autodesk.Inventor.Interop.dll
    :return: the ``Inventor`` .NET namespace module
    """
    global _module, _dll_path

    if _module is not None:
        if dll_path and os.path.normcase(dll_path) != os.path.normcase(_dll_path):
            logger.warning(
                f"Inventor Interop already loaded from {_dll_path}; ignoring {dll_path}"
            )
        return _module

    try:
        import clr
    except ImportError:
        raise InventorConnectionError(
            "pythonnet is required. Install with: pip install pythonnet"
        )

    dll_path = dll_path or find_inventor_dll()
    if not dll_path or not os.path.exists(dll_path):
        raise InventorVersionNotFoundError(
            "Inventor Interop DLL not found. Please provide inventor_path parameter."
        )

    try:
        clr.AddReference(dll_path)
        clr.AddReference("System")
        import Inventor
    except Exception as e:
        raise InventorConnectionError(f"Failed to load Inventor Interop DLL: {e}")

    _module = Inventor
    _dll_path = dll_path
    logger.info(f"Loaded Inventor Interop from: {dll_path}")
    return _module


class _LazyInterop(object):
    """
    Stand-in for the ``Inventor`` .NET namespace.

    Safe to import anywhere at any time; the assembly is loaded on first
    attribute access, e.g. ``InventorInterop.SurfaceBody``.
    """

    def __getattr__(self, name):
        return getattr(load_interop(), name)

    def __dir__(self):
        return dir(load_interop())

    def __repr__(self):
        if _module is None:
            return "<InventorInterop (not loaded)>"
        return f"<InventorInterop loaded from {_dll_path}>"


InventorInterop = _LazyInterop()
