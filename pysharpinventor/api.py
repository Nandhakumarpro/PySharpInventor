#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    pysharpinventor.api
    ~~~~~~~~~~~~~~~~~~~~

    Main Inventor automation object.

    :copyright: (c) 2026
    :license: BSD, see LICENSE.txt for more details.
"""

import logging

from pysharpinventor._interop import (
    InventorInterop,
    InventorConnectionError,
    InventorVersionNotFoundError,
    load_interop,
)

__all__ = ['Inventor', 'InventorInterop', 'INVENTOR',
           'InventorConnectionError', 'InventorVersionNotFoundError']

class INVENTOR:
    pass

logger = logging.getLogger(__name__)


class Inventor(object):
    """Main Inventor Automation object"""

    def __init__(self, create_if_not_exists=False, visible=True, inventor_path=None):
        """
        :param create_if_not_exists: if Inventor doesn't run, then
                                     new instance will be created
        :param visible: new Inventor instance will be visible if True (default)
        :param inventor_path: Optional path to Inventor Interop DLL
        """
        self._create_if_not_exists = create_if_not_exists
        self._visible = visible
        self._app = None
        self._inventor_path = inventor_path
        load_interop(inventor_path)  # Load CLR modules immediately

    @property
    def app(self):
        """Returns active Inventor Application"""
        if self._app is None:
            try:
                import System

                # Try to get active Inventor instance
                try:
                    raw_app = System.Runtime.InteropServices.Marshal.GetActiveObject("Inventor.Application")
                    self._app = InventorInterop.Application(raw_app)
                    logger.info("Connected to active Inventor instance")
                except System.Runtime.InteropServices.COMException:
                    if not self._create_if_not_exists:
                        raise InventorConnectionError(
                            "Inventor is not running. Set create_if_not_exists=True to start it."
                        )

                    # Create new Inventor instance
                    try:
                        inventor_type = System.Type.GetTypeFromProgID("Inventor.Application")
                        raw_app = System.Activator.CreateInstance(inventor_type)
                        self._app = InventorInterop.Application(raw_app)
                        self._app.Visible = self._visible
                        logger.info("Created new Inventor instance")
                    except Exception as e:
                        raise InventorConnectionError(f"Failed to create Inventor instance: {e}")

            except Exception as e:
                if isinstance(e, (InventorConnectionError, InventorVersionNotFoundError)):
                    raise
                raise InventorConnectionError(f"Failed to connect to Inventor: {e}")

        return self._app

    @property
    def doc(self):
        """Returns active document"""
        try:
            return InventorInterop.Document(self.app.ActiveDocument)
        except Exception as e:
            raise InventorConnectionError(f"Failed to get active document: {e}")

    def cast_document(self, document, target_type=None):
        """
        Explicitly cast document to specific type
        
        :param document: Document object to cast
        :param target_type: Target document type (e.g., InventorInterop.PartDocument)
        :return: Casted document object
        """
        if target_type:
            return target_type(document)
        
        # Auto-detect document type based on DocumentType
        doc_type = document.DocumentType
        
        type_mapping = {
            InventorInterop.DocumentTypeEnum.kUnknownDocumentObject: InventorInterop.Document,
            InventorInterop.DocumentTypeEnum.kPartDocumentObject: InventorInterop.PartDocument,
            InventorInterop.DocumentTypeEnum.kAssemblyDocumentObject: InventorInterop.AssemblyDocument,
            InventorInterop.DocumentTypeEnum.kDrawingDocumentObject: InventorInterop.DrawingDocument,
            InventorInterop.DocumentTypeEnum.kPresentationDocumentObject: InventorInterop.PresentationDocument,

        }
        
        document_class = type_mapping.get(doc_type, InventorInterop.Document)
        return document_class(document)

    #: Same as :attr:`doc`
    ActiveDocument = doc

    #: Same as :attr:`app`
    Application = app
