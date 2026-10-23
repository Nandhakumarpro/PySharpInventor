PySharpInventor - Autodesk Inventor Automation for Python
=========================================================

This library aims to simplify writing .NET/CLR Automation scripts for Autodesk Inventor with Python.

Requires:
---------

- pythonnet>=3.0.0
- Autodesk Inventor (2020+)

Features:
---------

- Dynamic Inventor version detection (picks the newest installed version)
- Efficient objects iteration and searching
- .NET/CLR interface to Inventor API
- Document type casting (Part, Assembly, Drawing, Presentation)
- Custom error handling with specific exceptions
- Support for connecting to active Inventor instances or creating new ones

Installation:
-------------

.. code-block:: bash

    pip install pysharpinventor

Usage Example:
--------------

.. code-block:: python

    from pysharpinventor import Inventor, InventorInterop

    # Connect to active Inventor instance
    inv = Inventor()
    
    # Or create new instance if Inventor is not running
    inv = Inventor(create_if_not_exists=True)

    # Or point at a specific Inventor Interop DLL
    inv = Inventor(inventor_path=r"C:\Program Files\Autodesk\Inventor 2025\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll")
    
    # Access active document
    doc = inv.doc
    
    # Cast document to specific type
    part_doc = inv.cast_document(doc, InventorInterop.PartDocument)
    
    # Or auto-detect document type
    casted_doc = inv.cast_document(doc)

Links
-----

- **Documentation** at `readthedocs.org <https://pysharpinventor.readthedocs.io/>`_
- **Source code** at `GitHub <https://github.com/Nandhakumarpro/pysharpinventor>`_
